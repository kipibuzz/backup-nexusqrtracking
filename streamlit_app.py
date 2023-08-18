import streamlit as st
import snowflake.connector
import matplotlib.pyplot as plt
import numpy as np
import cv2
from pyzbar.pyzbar import decode
import qrcode
import os
import io

# Snowflake connection parameters
CONNECTION_PARAMETERS = {
    "account": st.secrets['account'], 
    "user": st.secrets['user'],
    "password": st.secrets['password'],
    "database": st.secrets['database'],
    "schema": st.secrets['schema'],
    "warehouse": st.secrets['warehouse'],
}

# Function to mark attendance based on QR code
def mark_attendance_by_qr(qr_data):
    conn = snowflake.connector.connect(
        user=CONNECTION_PARAMETERS['user'],
        password=CONNECTION_PARAMETERS['password'],
        account=CONNECTION_PARAMETERS['account'],
        warehouse=CONNECTION_PARAMETERS['warehouse'],
        database=CONNECTION_PARAMETERS['database'],
        schema=CONNECTION_PARAMETERS['schema']
    )
    cursor = conn.cursor()

    # Check if attendee exists and has not attended
    cursor.execute(
        f"SELECT ATTENDEE_ID, ATTENDED FROM EMP WHERE QR_CODE = '{qr_data}'"
    )
    row = cursor.fetchone()
    if row:
        attendee_id, attended = row
        if attended:
            message = f'Attendance already marked for Attendee ID: {attendee_id}'
        else:
            # Mark attendance
            cursor.execute(
                f"UPDATE EMP SET ATTENDED = TRUE WHERE ATTENDEE_ID = '{attendee_id}'"
            )
            conn.commit()
            message = f'Attendance marked successfully for Attendee ID: {attendee_id}'
    else:
        message = 'Invalid QR code'

    cursor.close()
    conn.close()
    return message

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
        new_qr_codes_generated = generate_and_store_qr_codes()
        if new_qr_codes_generated > 0:
            st.success(f"{new_qr_codes_generated} new QR codes generated and stored successfully!")
        elif new_qr_codes_generated == 0:
            st.info("No new QR codes generated. QR codes already exist for all attendees.")
        else:
            st.warning("QR codes could not be generated. Please check for any issues.")

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
            
            result_message = mark_attendance_by_qr(qr_data)
            if 'successfully' in result_message:
                st.success(result_message)
            else:
                st.error(result_message)
                
# elif menu_choice == menu_choices["Attendance Statistics"]:
#     # Attendance statistics page
#     st.header('Attendance Statistics')
#     # ... (rest of your code for attendance statistics)

 
elif menu_choice == menu_choices["Attendance Statistics"]:
    # Attendance statistics page
    st.header('Attendance Statistics')

    # # # Query attendance data
    # # attendance_data = query_attendance_data()

    # # Generate statistics
    # statistics = generate_attendance_statistics(attendance_data)

    # total_attended = statistics['Total Attended']
    
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

 

