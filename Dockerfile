FROM python:3.13-slim-bookworm

# Create a non root user
RUN useradd -u 1000 -d /home/pyuser -m pyuser && \
    install -d -o pyuser -g pyuser /database && \
    apt-get update && \
    apt-get install -y git curl && \
    pip install --upgrade pip

# Switch user so container is run as non-root user
USER 1000

# Set environment
ENV PATH="/home/pyuser/.local/bin:$PATH"

# Copy the app to the container
COPY --chown=pyuser:pyuser . /home/pyuser/logger

WORKDIR /home/pyuser/logger

# Install the application
RUN pip install .

# Run the application using the script defined in pyproject.toml
ENTRYPOINT ["logger"]