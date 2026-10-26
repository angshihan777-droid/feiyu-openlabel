import { addCollection } from '@iconify/vue'
import { iconCollections } from 'virtual:feiyu-icons'

for (const collection of iconCollections) {
  addCollection(collection)
}
