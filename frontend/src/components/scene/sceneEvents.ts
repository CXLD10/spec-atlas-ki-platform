/* Tiny event bus for decoupled scene communication */
/* CitationChip emits 'fly-to-node', GraphScene subscribes */

type EventHandler<T> = (data: T) => void

interface SceneEventMap {
  'fly-to-node': string // nodeId
}

class SceneEventBus {
  private listeners: Map<keyof SceneEventMap, Set<EventHandler<any>>> = new Map()

  on<K extends keyof SceneEventMap>(event: K, handler: EventHandler<SceneEventMap[K]>) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set())
    }
    this.listeners.get(event)!.add(handler)
    return () => this.off(event, handler)
  }

  off<K extends keyof SceneEventMap>(event: K, handler: EventHandler<SceneEventMap[K]>) {
    this.listeners.get(event)?.delete(handler)
  }

  emit<K extends keyof SceneEventMap>(event: K, data: SceneEventMap[K]) {
    this.listeners.get(event)?.forEach((handler) => {
      try {
        handler(data)
      } catch (e) {
        console.error(`Error in event handler for ${String(event)}:`, e)
      }
    })
  }

  clear() {
    this.listeners.clear()
  }
}

export const sceneEvents = new SceneEventBus()
