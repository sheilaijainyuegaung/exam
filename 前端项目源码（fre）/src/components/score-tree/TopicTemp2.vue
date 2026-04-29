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
        <div class="select-box">
          <select v-model="config.type" class="select">
            <option :value="1">1模板</option>
            <option :value="2">2模板</option>
            <option :value="3">3模板</option>
            <option :value="4">4模板</option>
          </select>
        </div>
        <div class="select-box" v-if="isHasChild()">
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
import ScoreNode from "./Temp.vue";
import { calcTotalScore, isLevel3 } from "./temp";

export default {
  components: { ScoreNode },
  data() {
    return {
      node: undefined,
      parent: undefined,
      selId: "",
      list: [],
      config: { type: 1 },
      mateTempType: 1,
      autoType: 1,
    };
  },
  methods: {
    isLevel3,
    calcTotalScore,
    isHasChild() {
      return this.selId !== "" && this.node.childScores && this.node.childScores.length > 0;
    },
    setData(list, tType) {
      let type = tType;
      if (tType === 5) {
        type = 2;
      } else if (tType === 6) {
        type = 3;
      } else if (tType === 7) {
        type = 4;
      }
      this.list = list;
      this.config.type = type;
      this.mateTempType = tType;
      this.autoType = type;
      console.log("源数据:", list, type);
    },
    setTemp2(type, list) {
      this.setData(list, type);
    },
    getType() {
      if (this.autoType === this.config.type) {
        return this.mateTempType;
      }
      return this.config.type;
    },
    getList() {
      return this.list;
    },
    getPrevChildSum(index) {
      let sum = this.list.slice(0, index).reduce((sum, p) => sum + (p.childScores?.length || 0), 0);
      console.log("同级所有子和:", sum, index);
      return sum;
    },
    onSelItem(item, parent, selId) {
      this.node = item;
      if (this.node.type == null) {
        this.$set(this.node, "type", 1);
      }
      this.parent = parent;
      this.selId = selId;
      console.log("数据功能:", item, parent, selId);
    },
    addNode(node) {
      if (this.selId === "" || node === undefined) {
        this.list.push({
          score: 0,
          childScores: [],
        });
        return;
      }
      node.childScores ??= [];
      node.childScores.push({
        score: 0,
        childScores: [],
      });
    },
    delNode(node) {
      if (this.selId === "" || node === undefined) {
        this.list.pop();
        return;
      }
      node.childScores ??= [];
      node.childScores.pop();
    },
  },
};
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

.layout {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
}

.edit {
  font-size: 14px;
  div {
    margin-top: 4px;
  }
  button {
    background-color: #4a90e2;
    color: #fff;
    border: none;
    padding: 8px 16px;
    font-weight: 500;
    border-radius: 6px;
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
    box-shadow: 0 0 4px rgba(64, 158, 255, 0.4);
  }
}
</style>
