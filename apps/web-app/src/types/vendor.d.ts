declare module 'postal' {
  interface Channel {
    subscribe(event: string, callback: (message: Record<string, any>) => void): unknown
    publish(event: string, message: Record<string, any>): void
  }

  const postal: {
    channel(name: string): Channel
  }
  export default postal
}

declare module '@cloudgeek/vue3-video-player' {
  const plugin: any
  export default plugin
}

declare module 'element-plus/dist/locale/zh-cn.mjs' {
  const locale: any
  export default locale
}

declare module 'element-plus/dist/locale/en.mjs' {
  const locale: any
  export default locale
}

interface Window {
  opera?: string
}
