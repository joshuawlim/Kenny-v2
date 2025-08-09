FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline --no-audit --no-fund || npm i --no-audit --no-fund
COPY src ./src
EXPOSE 3000
ENV PORT=3000
CMD ["npm", "start"]


