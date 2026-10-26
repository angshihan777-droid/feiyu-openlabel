import { fileURLToPath } from 'node:url'
import { mergeConfig, defineConfig, configDefaults } from 'vitest/config'
import viteConfig from './vite.config'

const baseConfig = viteConfig({
  command: 'serve',
  mode: 'test',
  isSsrBuild: false,
  isPreview: false,
})

export default mergeConfig(
  baseConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      include: ['src/**/*.test.ts'],
      exclude: [...configDefaults.exclude, 'e2e/*', 'tests/**'],
      root: fileURLToPath(new URL('./', import.meta.url))
    }
  })
)
