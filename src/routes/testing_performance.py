import threading
import time

# Define the function to be run in the thread
def background_task():
    while not stop_thread:
        # Perform your background task here
        print("Background task is running...")
        time.sleep(1)  # Sleep for a while to simulate work

# Initialize a global variable to control the thread
stop_thread = False

# Start the thread before your script's main execution
thread = threading.Thread(target=background_task)
thread.start()

try:
    # Your main script logic here
    print("Main script is running...")
    time.sleep(10)  # Simulate main script work
finally:
    # Set the stop_thread flag to True to stop the background task
    stop_thread = True
    # Wait for the background thread to finish
    thread.join()
    print("Background task has ended.")
