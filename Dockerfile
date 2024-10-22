# Official python version
FROM python:3.13.0-alpine

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy the rest of the application code
COPY . .

# Run the command to start the bot
CMD ["python", "main.py"]
