<template>
  <div class="score-tree">
    <div class="score-wrap">
      <div ref="scoreBoard" :class="`score ${isLevel3(list)}`" @click="onUseTemp(getType(), list)">
        <ScoreNode
          v-for="(item, index) in list"
          :key="`root-${index}`"
          :index="index"
          :node="item"
          :id="`1-${index}`"
          :level="1"
          :order="getPrevChildSum(index)"
          :config="config"
          :selId="selId"
          :selItem="onSelItem"
          :onChanged="notifyChanged"
        />
      </div>
      <div class="export-row">
        <button class="export-btn" @click.stop="exportStructureJson">导出结构JSON</button>
      </div>
    </div>

    <div v-if="showEditUi" class="edit">
      <div class="total">满分{{ calcTotalScore(list) }}</div>

      <button @click="addNode(parent)">加平级</button>
      <button @click="delNode(parent)">减平级</button>
      <button @click="addNode(node)">加子级</button>
      <button @click="delNode(node)">减子级</button>

      <div class="select-box">
        <select v-model.number="config.type" class="select" @change="notifyChanged">
          <option :value="1">1模板</option>
          <option :value="2">2模板</option>
          <option :value="3">3模板</option>
          <option :value="4">4模板</option>
        </select>
      </div>
      <div class="select-box" v-if="isHasChild()">
        <select v-model.number="node.type" class="select" @change="notifyChanged">
          <option :value="1">序号</option>
          <option :value="2">划线</option>
        </select>
      </div>
    </div>
  </div>
</template>

<script>
import ScoreNode from "./ScoreNode.vue";
import { calcTotalScore, isLevel3 } from "./util";

function normalizeNode(rawNode) {
  const children = Array.isArray(rawNode && rawNode.childScores) ? rawNode.childScores : [];
  return {
    numbering:
      rawNode && rawNode.numbering !== undefined && rawNode.numbering !== null
        ? String(rawNode.numbering)
        : "",
    rawText: rawNode && rawNode.rawText ? String(rawNode.rawText) : "",
    score:
      rawNode && typeof rawNode.score === "number" && Number.isFinite(rawNode.score)
        ? rawNode.score
        : 0,
    type: rawNode && rawNode.type ? rawNode.type : 1,
    childScores: children.map((child) => normalizeNode(child)),
  };
}

export default {
  name: "TopicTemp",
  components: { ScoreNode },
  props: {
    onUseTemp: {
      type: Function,
      default: () => {},
    },
    showEditUi: {
      type: Boolean,
      default: true,
    },
    onSumScore: {
      type: Function,
      default: () => {},
    },
  },
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
      return (
        this.selId !== "" &&
        this.node &&
        Array.isArray(this.node.childScores) &&
        this.node.childScores.length > 0
      );
    },
    setData(list, tType) {
      let type = Number(tType) || 1;
      if (type === 5) {
        type = 2;
      } else if (type === 6) {
        type = 3;
      } else if (type === 7) {
        type = 4;
      }
      this.list = Array.isArray(list) ? list.map((item) => normalizeNode(item)) : [];
      this.config.type = type;
      this.mateTempType = Number(tType) || 1;
      this.autoType = type;
      this.node = undefined;
      this.parent = undefined;
      this.selId = "";
      this.notifyChanged();
    },
    setTemp(type, list) {
      this.setData(list, type);
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
      return this.list
        .slice(0, index)
        .reduce((sum, p) => sum + ((p && p.childScores && p.childScores.length) || 0), 0);
    },
    onSelItem(item, parent, selId) {
      this.node = item;
      if (this.node && this.node.type == null) {
        this.$set(this.node, "type", 1);
      }
      this.parent = parent;
      this.selId = selId;
    },
    createEmptyNode() {
      return {
        numbering: "",
        rawText: "",
        score: 0,
        type: 1,
        childScores: [],
      };
    },
    addNode(node) {
      if (this.selId === "" || node === undefined) {
        this.list.push(this.createEmptyNode());
        this.notifyChanged();
        this.scrollToBottom();
        return;
      }
      if (!Array.isArray(node.childScores)) {
        this.$set(node, "childScores", []);
      }
      node.childScores.push(this.createEmptyNode());
      this.notifyChanged();
      this.scrollToBottom();
    },
    delNode(node) {
      if (this.selId === "" || node === undefined) {
        this.list.pop();
        this.notifyChanged();
        return;
      }
      if (!Array.isArray(node.childScores) || node.childScores.length === 0) {
        return;
      }
      node.childScores.pop();
      this.notifyChanged();
    },
    notifyChanged() {
      const total = this.calcTotalScore(this.list);
      this.onSumScore(total);
      this.onUseTemp(this.getType(), this.list);
    },
    scrollToBottom() {
      const box = this.$refs.scoreBoard;
      if (!box) return;
      this.$nextTick(() => {
        box.scrollTop = box.scrollHeight;
      });
    },
    exportStructureJson() {
      const payload = {
        questionType: this.getType(),
        scores: this.list,
      };
      const text = JSON.stringify(payload, null, 2);
      const blob = new Blob([text], { type: "application/json;charset=utf-8" });
      const now = new Date();
      const stamp = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(
        now.getDate()
      ).padStart(2, "0")}_${String(now.getHours()).padStart(2, "0")}${String(now.getMinutes()).padStart(
        2,
        "0"
      )}${String(now.getSeconds()).padStart(2, "0")}`;
      const filename = `structure_${stamp}.json`;

      if (window.navigator && window.navigator.msSaveOrOpenBlob) {
        window.navigator.msSaveOrOpenBlob(blob, filename);
        return;
      }

      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    },
  },
};
</script>

<style scoped lang="scss">
.score-tree {
  display: flex;
  gap: 10px;
}

.score-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.score {
  height: 310px;
  width: 500px;
  overflow-y: auto;
  scrollbar-width: thin;
  background: #f7f5dd;
  border: 1px solid #d8d2b8;
  padding: 8px;
}

.layout {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
}

.export-row {
  display: flex;
  justify-content: flex-end;
}

.export-btn {
  min-height: 30px;
  padding: 0 10px;
  border-radius: 6px;
  border: 1px solid #3d8df7;
  background: #fff;
  color: #2f7de6;
  font-size: 13px;
  cursor: pointer;
}

.export-btn:hover {
  background: #edf4ff;
}

.edit {
  font-size: 13px;
  width: 92px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.total {
  font-size: 16px;
  margin-left: 4px;
  color: #111;
  font-weight: 600;
}

.edit button {
  background-color: #4a90e2;
  color: #fff;
  border: none;
  min-height: 32px;
  padding: 0 8px;
  border-radius: 6px;
  cursor: pointer;
}

.select-box {
  width: 100%;
}

.select {
  width: 100%;
  min-height: 32px;
  padding: 0 6px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid #3d8df7;
}

.select:hover {
  border-color: #409eff;
}

.select:focus {
  outline: none;
  border-color: #409eff;
  box-shadow: 0 0 4px rgba(64, 158, 255, 0.4);
}

@media (max-width: 1200px) {
  .score-tree {
    flex-direction: column;
  }

  .score {
    width: 100%;
  }

  .edit {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
