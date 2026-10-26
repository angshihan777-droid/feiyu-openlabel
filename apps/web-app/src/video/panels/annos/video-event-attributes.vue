<template>
  <!-- {{ toolStates.selected.userData.anno.ol_type_ }} -->
  <el-form :model='toolStates' label-width="80px" label-position="left">
    <el-form-item label="类别">
      <el-row>
        <el-col :span="18"><el-input v-model="toolStates.selected.userData.anno.ol_type_" />
        </el-col>
        <el-col :span="6">
          <el-popover placement="bottom" width="550" trigger="click">
            <template #reference>
              <el-button>
                <Icon icon="lucide:arrow-down" class="el-icon--right" />
              </el-button>
            </template>
            <div>
              <TaxonomyTreeSelecter @change="handleClassChange" @buttonClick="handleTreeNodeClick" selectedValue='' />
            </div>
          </el-popover>
        </el-col>
      </el-row>
    </el-form-item>
    <el-form-item label="开始时间">
      <el-input-number
        v-model="toolStates.selected.userData.anno.frame_intervals[0].time_start"
        :min="0"
        :step="0.1"
        :precision="2"
        controls-position="right"
      />
    </el-form-item>
    <el-form-item label="结束时间">
      <el-input-number
        v-model="toolStates.selected.userData.anno.frame_intervals[0].time_end"
        :min="0"
        :step="0.1"
        :precision="2"
        controls-position="right"
      />
    </el-form-item>
  </el-form>
  <el-divider />
  <VueForm id="propertyForm" ref="propertyForm" v-model="attributesFormData" :schema="selectedObjTypeAttrSchema"
    :formProps="{ labelPosition: 'top' }" :formFooter="{ show: false }" @change="handleProptertyFormChange" />
</template>

<script lang="tsx" setup>
import { Icon } from "@iconify/vue"
import { ref, watch, computed } from 'vue'
import { ElRow, ElCol, ElInput, ElButton, ElPopover, ElInputNumber } from 'element-plus'
import TaxonomyTreeSelecter from '@/components/Taxonomy/TaxonomyTreeSelecter.vue'
import VueForm from '@lljj/vue3-form-element'
import { taxonomyState } from '@/states/TaxonomyState'
import { toolStates } from '../../tools/video-annotator'
import _ from 'lodash'

/**
 * 选择类别变化
 * @param value 选择的类别
 */
const handleClassChange = (value: string) => {
  // entityChannel.pub(entityChannel.Events.DefaultClassChanged, {
  //   data: value
  // })
  // toolStates.selectedFabricObj.userData.anno.object_type = value
  if (toolStates.selected) {
    toolStates.selected.userData.anno.object_type = value
  }
  toolStates.defaultObjType = value
  // changeSchema()
}
/**
 * 关闭tree
 */
const handleTreeNodeClick = (msg: any) => {
  // entityChannel.pub(entityChannel.Events.DefaultClassChanged, {
  //   data: msg.data.name
  // })
  handleClassChange(msg.data.name)
  // unref(popoverRef).hide()
}

const attributesFormData = computed({
  get: () => {
    const attr = _.get(toolStates, "selected.userData.anno.object_attributes", undefined)
    if (attr) {
      return attr
    } else {
      return {}
    }

    // 动态form默认值
    // if (taxonomyState.classNameToClass) {
    //   taxonomyState.classNameToClass.forEach((v, k) => {
    //     if (k === toolStates.defaultObjType) {
    //       const obj = {}
    //       _.forIn(v.properties, (value, key) => {
    //         _.set(obj, key, _.get(value, 'default', ''))
    //       })
    //       return obj
    //     }
    //   })
    // }
  },
  set: (val) => {
    // _.set(toolStates, "selected.userData.anno.object_attributes", val)
    toolStates.selected.userData.anno.object_attributes = val
    toolStates.selected.userData.anno.attributes.opType = 'update'
  }
})

const defaultSchema = {
  type: 'object',
  required: [],
  'ui:order': ['*'],
  properties: {
    tags: {
      type: 'string',
      title: 'tags'
    },
    annotation: {
      type: 'string',
      title: 'annotation'
    }
  }
}
const selectedObjTypeAttrSchema = ref<any>({})
selectedObjTypeAttrSchema.value = defaultSchema

/**
 * 属性面板变化
 */
const handleProptertyFormChange = () => {
  // if (!attrPanel.focused) return
  // const msg = {
  //   source: 'ui',
  //   data: {
  //     id: formData.id,
  //     attributes: attributesFormData.value
  //   }
  // }
  // entityChannel.pub(entityChannel.Events.Updated, msg)
}


const changeSchema = () => {
  const defaultObjType = toolStates.defaultObjType
  const classMap = taxonomyState.classNameToClass
  const selectedClass = classMap?.get(defaultObjType)
  if (selectedClass?.properties) {
    selectedObjTypeAttrSchema.value = {
      ...selectedClass,
      properties: selectedClass.properties,
    }
  } else {
    selectedObjTypeAttrSchema.value = defaultSchema
  }
}

watch([() => taxonomyState.ontology,
() => taxonomyState.ontologyClassNames], (newVal, oldVal) => {
  if (newVal[0] && newVal[1]) {
    toolStates.defaultObjType = 'default'
  }
}, {immediate: true, deep: true })

watch(() => taxonomyState.ontologyClassNames, (newVal) => {
  toolStates.setting.objTypes = Array.isArray(newVal) ? newVal : []
})

watch([() => toolStates.selected.userData.anno.ol_type_], (newVal, oldVal) => {
  changeSchema()
})

</script>
<style scoped>
.el-form-item {
  margin-bottom: 0px;
}
</style>
<style>
.genFormItem {
  margin-bottom: 0px;
}
</style>
