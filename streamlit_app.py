import streamlit as st
import snowflake.connector
import matplotlib.pyplot as plt
import numpy as np
import cv2
from pyzbar.pyzbar import decode
import qrcode
import os

# Snowflake connection parameters
CONNECTION_PARAMETERS = {
    "account": st.secrets['account'], 
    "user": st.secrets['user'],
    "password": st.secrets['password'],
    "database": st.secrets['database'],
    "schema": st.secrets['schema'],
    "warehouse": st.secrets['warehouse'],
}

# Directory to save QR code images
qr_codes_dir = "/path/to/qr_codes/"

# Function to generate and store QR codes for employees
def generate_and_store_qr_codes():
    conn = snowflake.connector.connect(
        user=CONNECTION_PARAMETERS['user'],
        password=CONNECTION_PARAMETERS['password'],
        account=CONNECTION_PARAMETERS['account'],
        warehouse=CONNECTION_PARAMETERS['warehouse'],
        database=CONNECTION_PARAMETERS['database'],
        schema=CONNECTION_PARAMETERS['schema']
    )
    cursor = conn.cursor()

    cursor.execute("SELECT ATTENDEE_ID, QR_CODE FROM EMP")
    employee_data = cursor.fetchall()

    for attendee_id, qr_code in employee_data:
        if qr_code:
            print(f"QR code already exists for Attendee ID: {attendee_id}")
            continue
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(attendee_id)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")

        qr_img_path = os.path.join(qr_codes_dir, f"{attendee_id}.png")
        qr_img.save(qr_img_path)

        cursor.execute(
            f"UPDATE EMP SET QR_CODE = '{qr_img_path}' WHERE ATTENDEE_ID = '{attendee_id}'"
        )
        conn.commit()

    cursor.close()
    conn.close()

# Streamlit app
st.title('NexusPassCheck')

# Custom menu options with emojis
menu_choices = {
    "Generate QR Codes": "🔐 Generate QR Codes",
    "QR Code Scanner": "📷 QR Code Scanner",
    "Attendance Statistics": "📊 Attendance Statistics",
}

menu_choice = st.sidebar.radio("Select Page", list(menu_choices.values()))

if menu_choice == menu_choices["Generate QR Codes"]:
    # Generate QR codes page
    st.header('Generate QR Codes')
    st.write("Click the button below to generate and store QR codes for employees.")
    
    if st.button('Generate QR Codes'):
        generate_and_store_qr_codes()
        st.success("QR codes generated and stored successfully!")

elif menu_choice == menu_choices["QR Code Scanner"]:
    # QR code scanner page
    st.header('QR Code Scanner')

    image = st.camera_input("Show QR code")

    if image is not None:
        bytes_data = image.getvalue()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

        decoded_objects = decode(cv2_img)

        for obj in decoded_objects:
            qr_data = obj.data.decode('utf-8')
            st.write(f"QR Code Data: {qr_data}")

elif menu_choice == menu_choices["Attendance Statistics"]:
    # Attendance statistics page
    st.header('Attendance Statistics')
    # ... (rest of your code for attendance statistics)


# Function to generate attendance statistics
def generate_attendance_statistics(data):
    total_attendees = len(data)
    total_attended = sum(1 for _, attended in data if attended)
    total_not_attended = total_attendees - total_attended
    return {
        "Total Attendees": total_attendees,
        "Total Attended": total_attended,
        "Total Not Attended": total_not_attended,
    }


# Streamlit app
st.title('NexusPassCheck')
 
# ... (rest of your code)

# Custom menu options with emojis
menu_choices = {
    "Verify Attendance": "✅ Verify Attendance",
    "Attendance Statistics": "📊 Attendance Statistics",
    "QR Code Scanner": "📷 QR Code Scanner"
}

menu_choice = st.sidebar.radio("Select Page", list(menu_choices.values()))

if menu_choice == menu_choices["Verify Attendance"]:
    # Verify attendance page
    st.header('Verify Attendance')
    verification_code = st.text_input('Enter Verification Code:')
    if st.button('Verify'):
        if verification_code:
            result_message = verify_and_mark_attendance(verification_code)
            if 'successfully' in result_message:
                st.success(result_message + " ✅")
            else:
                st.error(result_message + " ❌")
                
elif menu_choice == menu_choices["Attendance Statistics"]:
    # Attendance statistics page
    st.header('Attendance Statistics')

    # Query attendance data
    attendance_data = query_attendance_data()

    # Generate statistics
    statistics = generate_attendance_statistics(attendance_data)

    total_attended = statistics['Total Attended']
    
    # Create a visually appealing and bold visualization for total attended
    st.write(
        f"<div style='text-align: center;'>"
        f"<h1 style='font-size: 4rem; color: green; font-weight: bold;'>{total_attended}</h1>"
        f"<p style='font-size: 1.5rem;'>Attended</p>"
        f"</div>",
        unsafe_allow_html=True
    )
    
    # Add a divider to create separation
    st.markdown("<hr style='border-top: 2px solid #ccc;'>", unsafe_allow_html=True)
    
    # Create a pie chart for attendance breakdown
    plt.figure(figsize=(8, 6))
    
    labels = ["Attended", "Not Attended"]
    sizes = [total_attended, statistics['Total Not Attended']]
    colors = ["#86bf91", "#e74c3c"]
    
    def func(pct, allvalues):
        absolute = int(pct/100.*np.sum(allvalues))
        return "{:.1f}%\n({:d})".format(pct, absolute)
    
    plt.pie(sizes, labels=labels, colors=colors, autopct=lambda pct: func(pct, sizes))
    plt.axis('equal')  # Equal aspect ratio ensures the pie is circular.
    plt.title("Attendance Breakdown", fontsize=16)
    
    # Display the pie chart
    st.pyplot(plt)

 

