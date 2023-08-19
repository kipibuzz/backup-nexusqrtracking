import streamlit as st
import snowflake.connector
import matplotlib.pyplot as plt
import numpy as np
import cv2
from pyzbar.pyzbar import decode
import qrcode
import os
import io
import tempfile
import boto3
import botocore
import botocore.exceptions


attendance_status = {}

# Snowflake connection parameters
CONNECTION_PARAMETERS = {
    "account": st.secrets['account'], 
    "user": st.secrets['user'],
    "password": st.secrets['password'],
    "database": st.secrets['database'],
    "schema": st.secrets['schema'],
    "warehouse": st.secrets['warehouse'],
}
aws_access_key_id = st.secrets['access_key']
aws_secret_access_key = st.secrets['secret_key']
aws_region = st.secrets['region']
s3 = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region
    )

def generate_and_store_qr_codes():

    aws_access_key_id = st.secrets['access_key']
    aws_secret_access_key = st.secrets['secret_key']
    aws_region = st.secrets['region']
    conn = snowflake.connector.connect(
        user=CONNECTION_PARAMETERS['user'],
        password=CONNECTION_PARAMETERS['password'],
        account=CONNECTION_PARAMETERS['account'],
        warehouse=CONNECTION_PARAMETERS['warehouse'],
        database=CONNECTION_PARAMETERS['database'],
        schema=CONNECTION_PARAMETERS['schema']
    )
    cursor = conn.cursor()
    

    # Fetch attendee IDs from the EMP table
    cursor.execute("SELECT ATTENDEE_ID, QR_CODE FROM EMP")
    employee_data = cursor.fetchall()

    new_qr_codes_generated = 0  # Initialize the counter

    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region
    )

    for attendee_id, qr_code in employee_data:
        if qr_code:
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

        # Save QR code image as temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            qr_img.save(temp_file, format="PNG")

        # Upload QR code image to S3 bucket
        s3_file_name = f'qrcodes/{attendee_id}.png'
        s3.upload_file(temp_file.name, 'qrstore', s3_file_name)

        # Clean up temporary file
        os.unlink(temp_file.name)

        # Update QR_CODE column with S3 file path
        s3_file_path = f's3://qrstore/{s3_file_name}'
        update_query = "UPDATE EMP SET QR_CODE = %s WHERE ATTENDEE_ID = %s"
        cursor.execute(update_query, (s3_file_path, attendee_id))
        conn.commit()
        
        new_qr_codes_generated += 1  # Increment the counter
    cursor.close()
    conn.close()
 

    return new_qr_codes_generated

def mark_attendance(attendee_id):
    conn = snowflake.connector.connect(
        user=CONNECTION_PARAMETERS['user'],
        password=CONNECTION_PARAMETERS['password'],
        account=CONNECTION_PARAMETERS['account'],
        warehouse=CONNECTION_PARAMETERS['warehouse'],
        database=CONNECTION_PARAMETERS['database'],
        schema=CONNECTION_PARAMETERS['schema']
    )
    cursor = conn.cursor()

    # Update attendance status
    update_query = "UPDATE EMP SET ATTENDED = TRUE WHERE ATTENDEE_ID = %s"
    try:
        cursor.execute(update_query, (attendee_id,))
        conn.commit()
        st.success("Attendance marked successfully.")
    except Exception as e:
        st.error(f"Error while marking attendance: {e}")
        conn.rollback()

    # Close the cursor and connection
    cursor.close()
    conn.close()
    
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

# Custom menu options with emojis
menu_choices = {
    "Generate QR Codes": "🔐 Generate QR Codes",
    "QR Code Scanner": "📷 QR Code Scanner",
    "Attendance Statistics": "📊 Attendance Statistics",
}

menu_choice = st.sidebar.radio("Select Page", list(menu_choices.values()))

if st.button('Generate QR Codes'):
        new_qr_codes_generated = generate_and_store_qr_codes()
        if new_qr_codes_generated > 0:
            st.success(f"{new_qr_codes_generated} new QR codes generated and stored successfully!")
        elif new_qr_codes_generated == 0:
            st.info("No new QR codes generated. QR codes already exist for all attendees.")
        else:
            st.warning("QR codes could not be generated. Please check for any issues.")

# QR code scanner page
if menu_choice == menu_choices["QR Code Scanner"]:
    st.header('QR Code Scanner')

    image = st.camera_input("Show QR code")

    if image is not None:
        bytes_data = image.getvalue()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)

        decoded_objects = decode(cv2_img)

       for obj in decoded_objects:
           qr_data = obj.data.decode('utf-8')
           print(f"Scanned QR Code Data: {qr_data}")  # Add this line
           st.write(f"QR Code Data: {qr_data}")
    # Rest of the logic


            # Check if the scanned QR code exists in the S3 bucket (valid QR code)
            s3_file_name = f'qrcodes/{qr_data}.png'
            try:
                s3.head_object(Bucket='qrstore', Key=s3_file_name)  # Use your actual bucket name

                if qr_data in attendance_status:
                    if attendance_status[qr_data]:
                        st.warning("QR code already scanned and attendee marked.")
                    else:
                        attendance_status[qr_data] = True
                        mark_attendance(qr_data)  # Mark attendee as attended
                        st.success("QR code scanned successfully. Attendee marked as attended.")
                else:
                    st.warning("QR code scanned, but attendee not registered for the event.")
                    
            except botocore.exceptions.ClientError as e:
                if e.response['Error']['Code'] == "404":
                    st.error("Invalid QR code. Please try again.")
                else:
                    st.warning("An error occurred while processing the QR code.")



# elif menu_choice == menu_choices["Attendance Statistics"]:
#     # Attendance statistics page
#     st.header('Attendance Statistics')
#     # ... (rest of your code for attendance statistics)
           
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
