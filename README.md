### ECE-3824-Final-Project
## Project Proposal: IoT Desk Security Monitor
Course: ECE-3822 | Author: Dhruvil Patel & Samuel Georgi 

# 1. Project Overview
The IoT Desk Security Monitor is a smart surveillance system designed to monitor a personal workspace. Using a Raspberry Pi and a USB camera, the system detects motion and identifies "occupancy events." This data is then securely transmitted to a cloud-based backend and displayed on a web dashboard to show peak activity times and security logs.

# 2. Hardware Requirements
To keep the physical assembly minimal and focus on the data pipeline, the following hardware will be used:

Processor: Raspberry Pi (3, 4, or 5)

Sensor: Standard USB Webcam (Plug-and-Play)

Connectivity: Onboard WiFi for data transmission via tuiot

Storage: MicroSD card for the OS and local logging

# 3. The Data Pipeline
Collection: A Python script using the OpenCV library will process the camera feed locally on the Pi to detect motion.

Transmission: When motion is detected, the Pi sends an HTTP POST request containing the timestamp and event duration to a FastAPI backend.

Security: All transmissions will be protected using Token-Based Authentication (Bearer Tokens) to ensure only my device can write to my database.

Storage: Data will be stored in a MongoDB or PostgreSQL database (Cloud-hosted).

Visualization: A web-based dashboard will render charts (e.g., "Events per Hour") using Chart.js or Flask templates.

# 4. User Experience
The end user will be able to:

View a real-time "Status" (Occupied vs. Vacant).

See a historical bar chart of activity over the last 24 hours.

Check a "Security Log" of the most recent 10 motion events.

# 5. Goals
Basic Goal: Successful motion detection and data storage in the cloud with token protection.

Stretch Goal: Implement "Human Detection" (distinguishing between a person and a shifting shadow) or real-time desktop notifications.
