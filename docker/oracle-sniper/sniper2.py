import oci
import time
import random
from datetime import datetime
import urllib.request
import json


COMPARTMENT_ID = ""
SUBNET_ID = ""
IMAGE_ID = ""
SSH_PUBLIC_KEY = "" 

INSTANCE_NAME = ""
SHAPE = ""
OCPUS = 2.0
MEMORY_IN_GBS = 12.0
BOOT_VOLUME_SIZE_IN_GBS = 200
DISCORD_WEBHOOK_URL = ""
# =================================================

# Load local credentials 
config = oci.config.from_file(file_location=r"")
compute_client = oci.core.ComputeClient(config)

def send_discord_alert(instance_id):
    if not DISCORD_WEBHOOK_URL or "YOUR_WEBHOOK" in DISCORD_WEBHOOK_URL:
        return
        
    payload = {
        "embeds": [{
            "title": "🚨 ORACLE ARM SECURED! 🚨",
            "description": "The capacity loop was successful. Your server is now spinning up in Dubai.",
            "color": 5763719,
            "fields": [
                {"name": "Instance Name", "value": INSTANCE_NAME, "inline": True},
                {"name": "Specs", "value": f"{OCPUS} OCPUs / {MEMORY_IN_GBS}GB RAM", "inline": True},
                {"name": "Instance ID", "value": f"`{instance_id}`"}
            ],
            "footer": {"text": "Oracle Auto-Sniper"}
        }]
    }
    
    req = urllib.request.Request(
        DISCORD_WEBHOOK_URL, 
        data=json.dumps(payload).encode('utf-8'), 
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    
    try:
        urllib.request.urlopen(req)
        print("📲 Discord notification sent successfully!")
    except Exception as e:
        print(f"⚠️ Server created, but Discord alert failed: {e}")

def send_discord_log(message):
    """Sends a simple text log to Discord"""
    if not DISCORD_WEBHOOK_URL or "YOUR_WEBHOOK" in DISCORD_WEBHOOK_URL:
        return
    
    payload = {"content": message}
    req = urllib.request.Request(
        DISCORD_WEBHOOK_URL, 
        data=json.dumps(payload).encode('utf-8'), 
        headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
    )
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"⚠️ Discord log failed: {e}")

def launch_instance():
    request = oci.core.models.LaunchInstanceDetails(
        compartment_id=COMPARTMENT_ID,
        availability_domain="",
        shape=SHAPE,
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=OCPUS,
            memory_in_gbs=MEMORY_IN_GBS
        ),
        source_details=oci.core.models.InstanceSourceViaImageDetails(
            source_type="image",
            image_id=IMAGE_ID,
            boot_volume_size_in_gbs=BOOT_VOLUME_SIZE_IN_GBS
        ),
        create_vnic_details=oci.core.models.CreateVnicDetails(
            subnet_id=SUBNET_ID,
            assign_public_ip=True,
            display_name="primary-vnic"
        ),
        metadata={
            "ssh_authorized_keys": SSH_PUBLIC_KEY
        },
        display_name=INSTANCE_NAME
    )

    try:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Attempting creation...")
        response = compute_client.launch_instance(request)
        print("\n🎉 SUCCESS! Server provisioned completely.")
        print(f"Instance ID: {response.data.id}")
        send_discord_alert(response.data.id)
        return True
    except oci.exceptions.ServiceError as e:
        
        # Expected behavior: no ARM capacity in the region
        if "Out of host capacity" in e.message or e.status == 500:
            print(f"⏳ [CAPACITY FULL] No ARM servers available in Dubai. Retrying...")
            return False 
            
        # handle HTTP 429 Rate Limiting to prevent API bans
        elif "Too many requests" in e.message or e.status == 429:
            print(f"🛑 [RATE LIMIT HIT] We are firing too fast (HTTP 429). Absorbing block and waiting...")
            return False 
        
        # Fatal configuration or authentication errors
        else:
            print("\n" + "="*55)
            print("🚨 CRITICAL API REJECTION 🚨")
            print("="*55)
            print(f"HTTP Status  : {e.status}")
            print(f"Oracle Code  : {e.code} (Oracle's internal system code)")
            print(f"Exact Message: {e.message}")
            print(f"Target Field : {getattr(e, 'target', 'Not specified by API')}")
            print(f"Request ID   : {e.request_id}")
            print("="*55 + "\n")
            return "stop" 
            
           
    except oci.exceptions.ConnectTimeout:
        print(f"⏳ [NETWORK TIMEOUT] Oracle API gateway timed out. Re-establishing connection next cycle...")
        return False

    except oci.exceptions.RequestException as e:
        print(f"⏳ [CONNECTION ERROR] Transient network error occurred: {e}. Retrying...")
        return False

    return False

if __name__ == "__main__":
    print("Starting Oracle ARM Python Sniper with Discord Integration...")
    
  
    send_discord_log("🟢 **Oracle Sniper Online:** The capacity loop has officially started on your PC.")
    
    attempt = 1
    while True:
        status = launch_instance()
        if status is True or status == "stop":
            break
        
        print(f"Sleep cycle ongoing... (Attempt {attempt} completed)\n")
        
        #send a heartbeat ping every 40 attempts to confirm the containter is alive 
        if attempt % 40 == 0:
            send_discord_log(f"⏱️ **Heartbeat:** Sniper is still running. Completed {attempt} attempts so far.")
            
        attempt += 1
        sleep_time = random.randint(80,140)
        print(f"Waiting {sleep_time} seconds to evade rate limits...\n")
        time.sleep(sleep_time)
