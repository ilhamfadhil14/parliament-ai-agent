# Parliament AI Assistant

## Prerequisites

This project was built using **Python 3.10**. Ensure you have the correct version installed before proceeding.

## 1. Create and Activate the Conda Environment

To set up the required dependencies, create and activate a Conda environment using the following commands:

```bash
conda env create -f environment.yml
conda activate parliament
```

## 2. Running the Chat Application

Once the environment is set up, follow these steps to start or stop the chat application:

### Make the Script Executable

Before running the application, ensure the startup script has execution permissions:

```bash
chmod +x start-chat.sh
```

### Start the Chat Application

Run the following command to start the chat application:

```bash
./start-chat.sh start
```

### Stop the Chat Application

To stop the chat application, use:

```bash
./start-chat.sh stop
```

## 3. Monitoring the Application

You can monitor application logs by checking the `app.log` file:

```bash
tail -f app.log
```

This will display real-time log updates to help with debugging and monitoring.

---
Now you're all set to run and manage the chat application efficiently!
