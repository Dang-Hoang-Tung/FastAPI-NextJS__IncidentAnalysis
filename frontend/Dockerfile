# frontend/Dockerfile
FROM node:20

WORKDIR /app

# Install deps first (better caching)
COPY package.json package-lock.json* ./
RUN npm install

# Copy the rest of the frontend app
COPY . .

# Expose Next.js dev port
EXPOSE 3000

# Dev server
CMD ["npm", "run", "dev"]
