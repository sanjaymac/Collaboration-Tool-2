# Use an ultra-lightweight Python image for maximum System Efficiency
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install dependencies efficiently using Docker caching
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final minimal production image
FROM python:3.11-slim
WORKDIR /app

# Copy only the installed packages and app code to reduce image weight
COPY --from=builder /root/.local /root/.local
COPY . .

# Ensure local bin is on path
ENV PATH=/root/.local/bin:$PATH
# Google Cloud Run requires apps to listen on PORT 8080
ENV PORT=8080

# Expose the correct port for Cloud Run
EXPOSE 8080

# Security & Efficiency: Healthcheck ensures the container fails fast if the app crashes
HEALTHCHECK CMD curl --fail http://localhost:8080/_stcore/health || exit 1

# Entrypoint optimized for production Streamlit on Google Cloud
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
