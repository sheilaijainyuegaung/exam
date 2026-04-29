<template>
  <div class="page">
    <div class="left-panel">
      <RecognitionUploader
        @task-created="onTaskCreated"
        @task-failed="onTaskFailed"
        @task-finished="onTaskFinished"
        @task-list-cleared="onTaskListCleared"
      />

      <div class="meta-card">
        <div><strong>当前任务：</strong>{{ currentTaskId || "-" }}</div>
        <div><strong>试卷标题：</strong>{{ title || "-" }}</div>
        <div><strong>符号提取：</strong>{{ detailSymbolPreview }}</div>
        <div class="export-row">
          <button class="export-btn" @click="exportStructureJson" :disabled="!exportPayload">
            导出JSON
          </button>
        </div>
      </div>

      <TopicTemp ref="refTopic" />
    </div>

    <div class="divider"></div>

    <div class="right-panel">
      <h3>试卷预览</h3>
      <div class="preview-list">
        <div class="preview-item" v-for="(item, idx) in listImg" :key="`main-${idx}`">
          <iframe
            v-if="isPdf(item)"
            :src="pdfPreviewUrl(item)"
            class="preview-pdf"
            frameborder="0"
          />
          <img v-else :src="fileUrl(item)" alt="" class="preview-image">
        </div>
      </div>

      <h3>答案预览</h3>
      <div class="preview-list">
        <div class="preview-item" v-for="(item, idx) in answImg" :key="`answer-${idx}`">
          <iframe
            v-if="isPdf(item)"
            :src="pdfPreviewUrl(item)"
            class="preview-pdf"
            frameborder="0"
          />
          <img v-else :src="fileUrl(item)" alt="" class="preview-image">
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import RecognitionUploader from "@/components/RecognitionUploader.vue";
import TopicTemp from "@/components/score-tree/TopicTemp2.vue";
import { apiBaseUrl } from "@/services/recognitionApi";

export default {
  name: "HelloWorld",
  components: { RecognitionUploader, TopicTemp },
  data() {
    return {
      listImg: [],
      answImg: [],
      title: "",
      currentTaskId: "",
      detailSymbolPreview: "-",
      exportPayload: null,
    };
  },
  methods: {
    onTaskCreated(payload) {
      if (payload && payload.taskIds && payload.taskIds.length > 0) {
        this.currentTaskId = payload.taskIds[0];
      }
    },
    onTaskFailed(payload) {
      const msg = payload && payload.errorMessage ? payload.errorMessage : "任务失败";
      this.detailSymbolPreview = msg;
    },
    onTaskListCleared() {
      this.listImg = [];
      this.answImg = [];
      this.title = "";
      this.currentTaskId = "";
      this.detailSymbolPreview = "-";
      this.exportPayload = null;
      if (this.$refs.refTopic && typeof this.$refs.refTopic.setTemp2 === "function") {
        this.$refs.refTopic.setTemp2(1, []);
      }
    },
    onTaskFinished(payload) {
      const { taskId, result, details } = payload;
      this.currentTaskId = taskId;
      this.listImg = result.mainPages || [];
      this.answImg = result.answerPages || [];
      this.title = `任务 ${taskId} 识别完成`;

      const topicList =
        result && result.scores && Array.isArray(result.scores.childScores)
          ? result.scores.childScores
          : [];
      this.$refs.refTopic.setTemp2(result.questionType || 1, topicList);
      this.exportPayload = {
        questionType: result.questionType || 1,
        scores: result && result.scores ? result.scores : { score: 0, childScores: [] },
        outlineItems: details && Array.isArray(details.outlineItems) ? details.outlineItems : [],
      };

      const symbols = details && Array.isArray(details.symbolTexts) ? details.symbolTexts : [];
      this.detailSymbolPreview = symbols.length ? symbols.slice(0, 3).join(" | ") : "暂无";
    },
    exportStructureJson() {
      if (!this.exportPayload) return;
      const text = JSON.stringify(this.exportPayload, null, 2);
      const blob = new Blob([text], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const now = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      const filename = `structure_${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(
        now.getHours()
      )}${pad(now.getMinutes())}${pad(now.getSeconds())}.json`;
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    },
    fileUrl(path) {
      if (!path) return "";
      if (/^https?:\/\//i.test(path)) return path;
      return `${apiBaseUrl}${path}`;
    },
    isPdf(path) {
      return /\.pdf($|\?)/i.test(path || "");
    },
    pdfPreviewUrl(path) {
      const base = this.fileUrl(path);
      if (!base) return "";
      const joiner = base.includes("#") ? "&" : "#";
      return `${base}${joiner}toolbar=0&navpanes=0&scrollbar=0&view=FitH`;
    },
  },
};
</script>

<style scoped>
.page {
  display: flex;
  height: 100%;
}

.left-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  overflow-y: auto;
}

.divider {
  width: 1px;
  background: #dcdfe6;
}

.right-panel {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.meta-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fff;
  padding: 10px;
  line-height: 1.8;
  font-size: 13px;
}
.export-row {
  margin-top: 8px;
}
.export-btn {
  background: #409eff;
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}
.export-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.preview-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 14px;
}

.preview-item {
  border: 1px solid #e4e7ed;
}

.preview-image {
  width: 100%;
  display: block;
}

.preview-pdf {
  width: 100%;
  min-height: 720px;
  display: block;
}
</style>
