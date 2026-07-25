import discord
from discord.ext import commands, tasks
import subprocess
import os
import psutil
import time
import asyncio
from collections import defaultdict
import socket
import struct
import urllib.request
import json
import requests
# --- CONFIGURATION ---
TOKEN = os.environ.get('DISCORD_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_ID =   # YOUR unique Discord User ID 
ALERT_CHANNEL_ID =   # Channel ID where alerts/logs will be posted

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command('help')
# Global trackers for brute force detection
failed_attempts = defaultdict(list)

# --- CUSTOM SECURITY CHECK ---
def is_admin():
    async def predicate(ctx):
        if ctx.author.id != ADMIN_ID:
            await ctx.send("❌ **Access Denied:** You are not authorized to run this command.")
            return False
        return True
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    system_watchdog.start()
    ssh_log_monitor.start()
    
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    if channel:
        await channel.send("✅ **System Online:** Pi-Bot has successfully booted up. Type `!help` to see available commands.")

# --- COMMANDS ---

@bot.command(name='status')
async def check_status(ctx):
    """Shows basic server metrics like CPU, RAM, network usage, and temp"""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_c = int(f.read()) / 1000

        cpu_usage = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        
        disk = psutil.disk_usage('/')

        embed = discord.Embed(title="📊 Pi Server Status", color=discord.Color.blue())
        embed.add_field(name="🌡️ Temperature", value=f"{temp_c:.1f}°C", inline=True)
        embed.add_field(name="🧠 CPU Usage", value=f"{cpu_usage}%", inline=True)
        embed.add_field(name="🐏 RAM Usage", value=f"{ram.percent}% ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)", inline=False)
        embed.add_field(name="💾 Disk Space", value=f"{disk.percent}% used ({disk.free // (1024**3)}GB free)", inline=True)
        
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"⚠️ Error pulling metrics: {e}")
@bot.command(name='help')
async def custom_help(ctx):
    """Shows the custom welcome menu and command list"""
    
    embed = discord.Embed(
        title="🖥️ Pi Server Control Terminal",
        description="Welcome! Here are the available commands to monitor and manage the server.",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="📊 Diagnostics & Status",
        value=(
            "`!status` - View CPU, RAM, Disk, and Temp metrics\n"
            "`!tailstat` - View Tailscale routing and node status\n"
            "`!dockerstat` - List all running and stopped containers"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🔒 Admin Controls (Restricted)",
        value=(
            "`!dockerrestart <name>` - Force restart a specific container\n"
            "`!reboot` - Perform a hard reboot of the Raspberry P\ni"
            "`!wakeup` - Send a Wake-on-LAN packet to PC"
        ),
        inline=False
    )

    embed.add_field(
        name="🌐 Web & DNS Management",
        value=(
            "`!pihole` - View daily ad-blocking stats\n"
            "`!proxylogs` - View recent Nginx web traffic (Admin\n)"
            "`!proxyhosts` - Lists all active Nginx Proxy Manager hosts and their forwarding targets."
        ),
        inline=False
    )
    
    # Footer message
    embed.set_footer(text="Automated watchdog alerts are active in the background.")
    
    await ctx.send(embed=embed)
    
@bot.command(name='tailstat')
async def tailscale_status(ctx):
    """Shows current Tailscale routing status"""
    try:
        # Run tailscale status but only get the local node info
        output = subprocess.check_output(["tailscale", "status", "--peers=false"]).decode("utf-8").strip()
        await ctx.send(f"```text\n{output}\n```")
    except Exception as e:
        await ctx.send(f"⚠️ Failed to pull Tailscale status: {e}")

@bot.command(name='dockerstat')
async def docker_status(ctx):
    """Shows active and stopped docker containers"""
    try:
        cmd = ["docker", "ps", "-a", "--format", "table {{.Names}}\t{{.Status}}\t{{.State}}"]
        output = subprocess.check_output(cmd).decode("utf-8").strip()
        await ctx.send(f"```text\n{output}\n```")
    except Exception as e:
        await ctx.send(f"⚠️ Failed to pull Docker status: {e}")

@bot.command(name='dockerrestart')
@is_admin()
async def docker_restart(ctx, container_name: str):
    """Restarts a specific Docker container (Admin Only)"""
    await ctx.send(f"🔄 Attempting to restart container: `{container_name}`...")
    try:
        subprocess.check_call(["docker", "restart", container_name])
        await ctx.send(f"✅ Container `{container_name}` successfully restarted.")
    except subprocess.CalledProcessError:
        await ctx.send(f"❌ Failed to restart `{container_name}`. Verify the container name exists.")

@bot.command(name='reboot')
@is_admin()
async def reboot_server(ctx):
    """Reboots the physical Pi server (Admin Only)"""
    await ctx.send("🔄 **Command Received:** Rebooting the Raspberry Pi immediately. Going offline...")
    try:
        subprocess.Popen(["sudo", "reboot"])
    except Exception as e:
        await ctx.send(f"❌ Failed to invoke reboot: {e}")


@bot.command(name='wakeup')
@is_admin()
async def wake_pc(ctx):
    """Sends a Magic Packet to wake up the main PC (Admin Only)"""
    
    TARGET_MAC = ""  
    
    await ctx.send(f"🚀 **Command Received:** Broadcasting Magic Packet for `{TARGET_MAC}`...")

    try:
        mac_clean = TARGET_MAC.replace(':', '').replace('-', '')
        if len(mac_clean) != 12:
            raise ValueError("Invalid MAC address format.")

        data = bytes.fromhex(mac_clean)
        
        magic_packet = b'\xff' * 6 + data * 16

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(magic_packet, ('255.255.255.255', 9))

        await ctx.send("✅ **Success:** Magic packet sent! Your PC should be waking up.")
    except Exception as e:
        await ctx.send(f"❌ **Error:** Failed to send magic packet: {e}")



@bot.command(name='pihole')
async def pihole_stats(ctx):
    """Shows Pi-hole v6 ad-blocking statistics"""
    PIHOLE_URL = ""  
    APP_PASSWORD = "" 
    
    try:
        auth_url = f"{PIHOLE_URL}/api/auth"
        auth_resp = requests.post(auth_url, json={"password": APP_PASSWORD}, timeout=5)
        auth_resp.raise_for_status()
        sid = auth_resp.json().get("session", {}).get("sid")
        
        headers = {"X-FTL-SID": sid}
        stats_url = f"{PIHOLE_URL}/api/stats/summary"
        stats_resp = requests.get(stats_url, headers=headers, timeout=5)
        stats_resp.raise_for_status()
        
        data = stats_resp.json()
        
        queries = data.get('queries', {})

        status_counts = queries.get('status', {})

        ads_blocked = status_counts.get('GRAVITY', 0)

        total_queries= queries.get('total', 0)

        ratio = (ads_blocked / total_queries * 100) if total_queries > 0 else 0
        
        embed = discord.Embed(title="🛡️ Pi-hole Network Shield (v6)", color=discord.Color.green())
        embed.add_field(name="Blocked Today", value=f"**{ads_blocked:,}** domains", inline=True)
        embed.add_field(name="Network Block Ratio", value=f"**{ratio:.1f}%**", inline=True)
        embed.add_field(name="Total DNS Queries", value=f"{total_queries:,}", inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"⚠️ Failed to reach Pi-hole v6 API: {e}")
@bot.command(name='proxylogs')
@is_admin()
async def proxy_logs(ctx):
    """Tails the last 15 lines of the Nginx Proxy Manager logs (Admin Only)"""
    await ctx.send("🔍 Fetching recent proxy requests...")
    try:
        cmd = ["docker", "logs", "--tail", "15", "nginx-app-1"]
        output = subprocess.check_output(cmd).decode("utf-8")
        
        safe_output = output[-1900:] if len(output) > 1900 else output
        await ctx.send(f"```text\n{safe_output}\n```")
    except subprocess.CalledProcessError:
        await ctx.send("❌ Failed to read Nginx logs. Check the container name.")

@bot.command(name='proxyhosts')
async def list_proxy_hosts(ctx):
    """Lists all active Nginx Proxy Manager hosts"""
    NPM_URL = ""
    EMAIL = ""
    PASSWORD = ""
    
    try:
        login_resp = requests.post(f"{NPM_URL}/tokens", json={"identity": EMAIL, "secret": PASSWORD})
        login_resp.raise_for_status()
        token = login_resp.json().get("token")
        
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{NPM_URL}/nginx/proxy-hosts", headers=headers)
        resp.raise_for_status()
        hosts = resp.json()
        
        embed = discord.Embed(title="🌐 Active Proxy Hosts", color=discord.Color.blue())
        
        if not hosts:
            embed.description = "No proxy hosts found."
        
        for host in hosts:
            domains = ", ".join(host.get('domain_names', []))
            status = "🟢" if host.get('enabled') == 1 else "🔴"
            forward_to = f"{host.get('forward_scheme')}://{host.get('forward_host')}:{host.get('forward_port')}"
            
            embed.add_field(
                name=f"{status} {domains}", 
                value=f"Target: `{forward_to}`", 
                inline=False
            )
            
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"⚠️ Could not reach Nginx Proxy Manager: {e}")

# --- AUTOMATED WATCHDOG ALERTS (RAM, CPU, THERMALS) ---

@tasks.loop(seconds=60)
async def system_watchdog():
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    if not channel:
        return

    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_c = int(f.read()) / 1000
        if temp_c >= 75:
            await channel.send(f"⚠️ **THERMAL WARNING:** Pi CPU Temperature is dangerously high at **{temp_c:.1f}°C**!")

        cpu_usage = psutil.cpu_percent(interval=None)
        if cpu_usage >= 80:
            await channel.send(f"⚠️ **CPU SPIKE ALERT:** CPU utilization has reached **{cpu_usage}%**.")

        ram_usage = psutil.virtual_memory().percent
        if ram_usage >= 80:
            await channel.send(f"⚠️ **RAM EXHAUSTION ALERT:** System Memory utilization is at **{ram_usage}%**.")
            
    except Exception as e:
        print(f"Watchdog error: {e}")

# --- SSH LOGIN & BRUTE FORCE MONITOR (Real-time syslog tailing) ---

@tasks.loop(count=1)
async def ssh_log_monitor():
    await bot.wait_until_ready()
    channel = bot.get_channel(ALERT_CHANNEL_ID)
    if not channel:
        return

    # Use asyncio to launch the subprocess without blocking the main Discord heartbeat
    process = await asyncio.create_subprocess_exec(
        "journalctl", "-u", "ssh", "-f", "-n", "0",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    while True:
        # Await non-blocking stdout reads so the main Discord API heartbeat doesn't drop
        line_bytes = await process.stdout.readline()
        if not line_bytes:
            break
        
        line = line_bytes.decode("utf-8")
        
        if "Accepted password" in line or "Accepted publickey" in line:
            parts = line.split()
            user = "unknown"
            ip_addr = "unknown"
            for idx, part in enumerate(parts):
                if part == "for" and idx + 1 < len(parts): user = parts[idx+1]
                if part == "from" and idx + 1 < len(parts): ip_addr = parts[idx+1]
            
            await channel.send(f"🟢 **Successful SSH Login:** User `{user}` connected successfully from IP `{ip_addr}`.")

        elif "Failed password" in line:
            parts = line.split()
            user = "unknown"
            ip_addr = "unknown"
            for idx, part in enumerate(parts):
                if part == "invalid" and idx + 1 < len(parts): user = parts[idx+1]
                if part == "for" and idx + 1 < len(parts): user = parts[idx+1]
                if part == "from" and idx + 1 < len(parts): ip_addr = parts[idx+1]

            current_time = time.time()
            failed_attempts[ip_addr].append(current_time)
            
            failed_attempts[ip_addr] = [t for t in failed_attempts[ip_addr] if current_time - t < 300]
            
            if len(failed_attempts[ip_addr]) >= 3:
                await channel.send(
                    f"🚨 **BRUTE FORCE DETECTED:** IP address `{ip_addr}` has failed to log into account `{user}` "
                    f"**{len(failed_attempts[ip_addr])} times** within the last 5 minutes!"
                )

bot.run(TOKEN)
