FROM quay.io/astronomer/astro-runtime:12.0.0

# Install project dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy include modules
COPY include/ /usr/local/lib/python3.12/site-packages/include/
