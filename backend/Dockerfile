FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Run development server with auto-reload
CMD ["npm", "run", "dev"]
