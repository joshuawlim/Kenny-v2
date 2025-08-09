FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --prefer-offline --no-audit --no-fund || npm i --no-audit --no-fund
COPY src ./src
EXPOSE 80
ENV PORT=80
CMD ["npm", "start"]


