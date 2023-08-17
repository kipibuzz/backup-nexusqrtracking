import streamlit as st
import snowflake.connector
import pandas as pd
import matplotlib.pyplot as plt

# Snowflake connection parameters
CONNECTION_PARAMETERS = {
    "account": st.secrets['account'], 
    "user": st.secrets['user'],
    "password": st.secrets['password'],
    "database": st.secrets['database'],
    "schema": st.secrets['schema'],
    "warehouse": st.secrets['warehouse'],
}

# Function to verify and mark attendance
def verify_and_mark_attendance(verification_code):
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
        f"SELECT ATTENDEE_ID, ATTENDED FROM EMP WHERE CODE = '{verification_code}'"
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
            message = f'Code verified successfully for Attendee ID: {attendee_id}! They are marked as attended.'
    else:
        message = 'Invalid code'

    cursor.close()
    conn.close()
    return message

# Function to query attendance data
def query_attendance_data():
    conn = snowflake.connector.connect(
        user=CONNECTION_PARAMETERS['user'],
        password=CONNECTION_PARAMETERS['password'],
        account=CONNECTION_PARAMETERS['account'],
        warehouse=CONNECTION_PARAMETERS['warehouse'],
        database=CONNECTION_PARAMETERS['database'],
        schema=CONNECTION_PARAMETERS['schema']
    )
    cursor = conn.cursor()

    # Query attendance data
    cursor.execute("SELECT ATTENDEE_ID, ATTENDED FROM EMP")
    data = cursor.fetchall()

    cursor.close()
    conn.close()
    return data

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
st.title('Event Attendance Management')

# Navigation menu
menu_choice = st.sidebar.radio("Select Page", ["Verify Attendance", "Attendance Statistics"])

if menu_choice == "Verify Attendance":
    # Verify attendance page
    st.header('Verify Attendance')
    verification_code = st.text_input('Enter Verification Code:')
    if st.button('Verify'):
        if verification_code:
            result_message = verify_and_mark_attendance(verification_code)
            if 'successfully' in result_message:
                st.success(result_message)
            else:
                st.error(result_message)

elif menu_choice == "Attendance Statistics":
    # Attendance statistics page
    st.header('Attendance Statistics')

    # Query attendance data
    attendance_data = query_attendance_data()

    # Generate statistics
    statistics = generate_attendance_statistics(attendance_data)

    # Display statistics
    st.subheader('Overall Attendance Statistics')
    st.write(statistics)

    # Create a bar chart
    df = pd.DataFrame.from_records(attendance_data, columns=["ATTENDEE_ID", "ATTENDED"])
    df["ATTENDED"] = df["ATTENDED"].apply(lambda x: "Attended" if x else "Not Attended")
    st.subheader('Attendance Status Breakdown')
    chart = df["ATTENDED"].value_counts().plot(kind='bar')
    st.pyplot(chart)

# Close Snowflake connections (not shown in the code)
# ...
