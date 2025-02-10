# Author : Vongkeo KSV

# Pull the base image 
FROM node:18-alpine as build-stage

# Set working directory
WORKDIR /app

# Copy package.json and package-lock.json
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the application source code
COPY . .

# Expose port 3000 for the Node.js backend
EXPOSE 3050

# Start the application
CMD ["node", "server.js"]
