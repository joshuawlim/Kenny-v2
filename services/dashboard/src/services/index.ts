// Export all API services
export { gatewayAPI } from './gateway'
export { registryAPI } from './registry'
export { coordinatorAPI } from './coordinator'
export { ApiClient, ApiError } from './api'

// Helper function to check if all services are healthy
export const checkSystemHealth = async () => {
  try {
    const [gatewayHealth, registryHealth, coordinatorHealth] = await Promise.allSettled([
      gatewayAPI.getHealth(),
      registryAPI.getSystemHealth(),
      coordinatorAPI.getHealth(),
    ])

    return {
      gateway: gatewayHealth.status === 'fulfilled',
      registry: registryHealth.status === 'fulfilled',
      coordinator: coordinatorHealth.status === 'fulfilled',
      overall: [gatewayHealth, registryHealth, coordinatorHealth].every(
        result => result.status === 'fulfilled'
      ),
    }
  } catch (error) {
    return {
      gateway: false,
      registry: false,
      coordinator: false,
      overall: false,
      error,
    }
  }
}