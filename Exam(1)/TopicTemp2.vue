<template>
  <div class="score-tree">
    <div :class="`score ${isLevel3(list)}`">
      <ScoreNode
        v-for="(item,index) in list"
        :key="index"
        :index="index"
        :node="item"
        :id="`1-${index}`"
        :level="1"
        :order="getPrevChildSum(index)"
        :config="config"
        :selId="selId"
        :selItem="onSelItem"
      />
    </div>
    <div style="right: 22px;">
      <div class="edit">
        <div style="font-size: 15px;margin-left: 8px;color: black">满分{{ calcTotalScore(list) }}</div>
        <div>
          <button @click="addNode(parent)">加平级</button>
        </div>
        <div>
          <button @click="delNode(parent)">减平级</button>
        </div>

        <div>
          <button @click="addNode(node)">加子级</button>
        </div>
        <div>
          <button @click="delNode(node)">减子级</button>
        </div>
        <div  class="select-box">
          <select v-model="config.type" class="select">
            <option :value="1">1模板</option>
            <option :value="2">2模板</option>
            <option :value="3">3模板</option>
            <option :value="4">4模板</option>
          </select>
        </div>
        <div  class="select-box" v-if="isHasChild()">
          <select v-model="node.type" class="select">
            <option :value="1">序号</option>
            <option :value="2">划线</option>
          </select>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import ScoreNode from './Temp.vue'
import {calcTotalScore, isLevel3} from "./temp";

export default {
  components: {ScoreNode},
  data(){
    return {
      node:undefined,//当前选择的节点
      parent:undefined,//当前节点的父节点
      selId:"",//选中的id
      list:[],//源数据
      config:{type:1},//配置
      mateTempType:1,//由于安卓部分需要567,这里临时保存。
      autoType:1,//如果和config.type不一样。否则就返回config.type。因为config.type可以被修改
    }
  },
  methods: {
    isLevel3,
    calcTotalScore,
    isHasChild(){
      // 在选中节点的情况判断是否有子级
      return this.selId !== "" && this.node.childScores && this.node.childScores.length > 0
    },
    setData(list,tType){
      let type = tType;
      if (tType === 5) {
        type = 2
      } else if (tType === 6) { //不带序号
        type = 3
      } else if (tType === 7) { //带序号
        type = 4
      }
      this.list = list
      this.config.type = type
      this.mateTempType = tType;
      this.autoType = type;
      console.log("源数据:",list,type)
    },
    setTemp2(type,list){ // 兼容方法
      this.setData(list,type)
    },
    getType(){ //这里返回的是js中提取结构的类型
      if (this.autoType === this.config.type) {
        return this.mateTempType
      }
      return this.config.type
    },
    getList(){
      return this.list
    },
    getPrevChildSum(index) {
      let sum = this.list
        .slice(0, index)
        .reduce((sum, p) => sum + (p.childScores?.length || 0), 0)
      console.log("同级所有子和:",sum,index)
      return sum
    },
    onSelItem(item,parent,selId){
      this.node = item
      if (this.node.type == null) { // 优化变成响应式
        this.$set(this.node,"type",1)
      }
      this.parent = parent
      this.selId = selId
      console.log("数据功能:",item,parent,selId)
    },
    addNode(node){
      if(this.selId === "" || node === undefined){
        this.list.push({
          score: 0,
          childScores: [],
        })
        return;
      }
      node.childScores ??= []
      node.childScores.push({
        score: 0,
        childScores: [],
      })
    },
    delNode(node){
      if(this.selId === "" || node === undefined){
        this.list.pop()
        return;
      }
      node.childScores ??= []
      node.childScores.pop()
    },
  }
}
</script>
<style scoped lang="scss">
.score-tree {
  display: flex;
}

.score {
  height: 310px;
  width: 500px;
  overflow-y: scroll;
  scrollbar-width: thin;
  background: beige;
}

.layout{
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
}

.edit {
  font-size: 14px;
  div {
    margin-top: 4px;
  }
  /* 基础按钮样式 */
  button {
    background-color: #4a90e2; /* 蓝色背景 */
    color: #fff; /* 白色文字 */
    border: none; /* 去掉默认边框 */
    padding: 8px 16px; /* 内边距 */
    font-weight: 500;
    border-radius: 6px; /* 圆角 */
    cursor: pointer;
  }
}

.select-box {
  width: 75px;
  .select {
    width: 100%;
    padding: 6px 6px;
    border-radius: 6px;
    font-size: 12px;
    cursor: pointer;
  }
  .select:hover {
    border-color: #409eff;
  }
  .select:focus {
    outline: none;
    border-color: #409eff;
    box-shadow: 0 0 4px rgba(64,158,255,.4);
  }
}
</style>
