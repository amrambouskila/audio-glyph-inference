FROM node:22-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL=http://localhost:8220
ARG VITE_WS_URL=ws://localhost:8220/ws/live
ARG VITE_AUDIO_SAMPLE_RATE_HZ=16000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_AUDIO_SAMPLE_RATE_HZ=$VITE_AUDIO_SAMPLE_RATE_HZ
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
