FROM node:22-slim AS build
WORKDIR /app/client
COPY client/package*.json ./
RUN npm install
COPY client/ ./
RUN npm run build

FROM node:22-slim
WORKDIR /app/server
COPY server/package*.json ./
RUN npm install --omit=dev
COPY server/ ./
RUN npm run build
COPY --from=build /app/client/dist /app/client/dist

ENV PORT=4000
ENV DB_PATH=/app/data/lms.sqlite3
VOLUME ["/app/data"]
EXPOSE 4000
CMD ["node", "dist/index.js"]
