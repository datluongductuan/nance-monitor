FROM python:3.8

WORKDIR /app

# Copy your application code to the container
COPY . /app

# Install dependencies
RUN pip install -r requirements.txt

# Run the application
CMD python main.py
