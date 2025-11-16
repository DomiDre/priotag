# Development stage - Using standard node image to avoid musl issues
FROM node:24 AS development

WORKDIR /app
RUN chown -R node:node /app

USER node

# Copy package files
COPY --chown=node:node package*.json ./

# Install dependencies with clean slate
RUN npm ci

# Copy source code
COPY --chown=node:node . .

# Expose port for Vite dev server
EXPOSE 5173

# Run development server with proper host binding
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]


# Build stage
FROM node:24 AS builder

# Build arguments for metadata
ARG BUILD_VERSION="unknown"
ARG BUILD_COMMIT="unknown"
ARG BUILD_DATE="unknown"

WORKDIR /app
RUN chown -R node:node /app

USER node

# Copy package files
COPY --chown=node:node package*.json ./

# Clean install dependencies
RUN npm ci

# Copy source code
COPY --chown=node:node . .

# Create build info file for injection
RUN echo "{\"version\":\"$BUILD_VERSION\",\"commit\":\"$BUILD_COMMIT\",\"build_date\":\"$BUILD_DATE\",\"source_url\":\"https://github.com/DomiDre/priotag/tree/$BUILD_COMMIT\"}" > static/build-info.json

# Build the SvelteKit app
RUN npm run build


# Production stage
FROM node:24-alpine AS production

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nodejs -u 1001

# Copy package files first
COPY --from=builder --chown=nodejs:nodejs /app/package*.json ./

# Install only production dependencies
RUN npm ci --only=production && \
    npm cache clean --force

# Copy built application
COPY --from=builder --chown=nodejs:nodejs /app/build ./build

# If you're using @sveltejs/adapter-node, also copy these:
# COPY --from=builder --chown=nodejs:nodejs /app/.svelte-kit ./.svelte-kit

# Switch to non-root user
USER nodejs

# Expose port
EXPOSE 3000

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start the application
CMD ["node", "build"]
