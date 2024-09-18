import streamlit as st
import cv2
import numpy as np
import base64
import requests
import json
import time
import random
import os

# Function to handle the try-on process
def tryon(person_img, garment_img, seed, randomize_seed):
    if person_img is None or garment_img is None:
        st.warning("Empty image")
        return None, None, "Empty image"
    if randomize_seed:
        seed = random.randint(0, MAX_SEED)
    
    encoded_person_img = cv2.imencode('.jpg', cv2.cvtColor(person_img, cv2.COLOR_RGB2BGR))[1].tobytes()
    encoded_person_img = base64.b64encode(encoded_person_img).decode('utf-8')
    encoded_garment_img = cv2.imencode('.jpg', cv2.cvtColor(garment_img, cv2.COLOR_RGB2BGR))[1].tobytes()
    encoded_garment_img = base64.b64encode(encoded_garment_img).decode('utf-8')

    url = "http://" + os.environ['tryon_url'] + "Submit"
    token = os.environ['token']
    cookie = os.environ['Cookie']
    referer = os.environ['referer']
    headers = {'Content-Type': 'application/json', 'token': token, 'Cookie': cookie, 'referer': referer}
    data = {
        "clothImage": encoded_garment_img,
        "humanImage": encoded_person_img,
        "seed": seed
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data), timeout=50)
        if response.status_code == 200:
            result = response.json()['result']
            status = result['status']
            if status == "success":
                uuid = result['result']
    except Exception as err:
        st.error(f"Post Exception Error: {err}")
        return None, None, "Too many users, please try again later"

    time.sleep(9)
    Max_Retry = 12
    result_img = None
    info = ""
    for i in range(Max_Retry):
        try:
            url = "http://" + os.environ['tryon_url'] + "Query?taskId=" + uuid
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                result = response.json()['result']
                status = result['status']
                if status == "success":
                    result = base64.b64decode(result['result'])
                    result_np = np.frombuffer(result, np.uint8)
                    result_img = cv2.imdecode(result_np, cv2.IMREAD_UNCHANGED)
                    result_img = cv2.cvtColor(result_img, cv2.COLOR_RGB2BGR)
                    info = "Success"
                    break
                elif status == "error":
                    info = "Error"
                    break
            else:
                info = "URL error, please contact the admin"
                break
        except requests.exceptions.ReadTimeout:
            info = "Http Timeout, please try again later"
        except Exception as err:
            info = f"Get Exception Error: {err}"
        time.sleep(1)
    
    if info == "":
        info = f"No image after {Max_Retry} retries"
    if info != "Success":
        st.warning("Too many users, please try again later")

    return result_img, seed, info

MAX_SEED = 999999

# Set up the Streamlit app
st.set_page_config(page_title="Virtual Try-On", page_icon=":guardsman:", layout="wide")

st.title("Virtual Try-On")
st.markdown("""
**Step 1:** Upload a person image ⬇️  
**Step 2:** Upload a garment image ⬇️  
**Step 3:** Press “Run” to get try-on results
""")

col1, col2 = st.columns(2)

with col1:
    person_img = st.file_uploader("Person Image", type=["jpg", "jpeg", "png"])
    
with col2:
    garment_img = st.file_uploader("Garment Image", type=["jpg", "jpeg", "png"])

if person_img and garment_img:
    person_img = np.array(bytearray(person_img.read()), dtype=np.uint8)
    garment_img = np.array(bytearray(garment_img.read()), dtype=np.uint8)
    person_img = cv2.imdecode(person_img, cv2.IMREAD_COLOR)
    garment_img = cv2.imdecode(garment_img, cv2.IMREAD_COLOR)
    
    st.sidebar.header("Options")
    seed = st.sidebar.slider("Seed", 0, MAX_SEED, 0)
    randomize_seed = st.sidebar.checkbox("Random seed", value=True)

    if st.sidebar.button("Run"):
        result_img, seed_used, result_info = tryon(person_img, garment_img, seed, randomize_seed)
        if result_info == "Success":
            st.image(result_img, caption="Result", channels="BGR")
            st.sidebar.text(f"Seed used: {seed_used}")
        else:
            st.sidebar.error(result_info)
else:
    st.sidebar.warning("Please upload both images to proceed.")
