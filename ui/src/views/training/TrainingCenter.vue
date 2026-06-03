<template>
  <div class="page-container">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="培训中心" name="learning">
        <div class="summary-grid" v-loading="loadingOverview">
          <el-card shadow="never" class="summary-card">
            <div class="summary-label">课程数</div>
            <div class="summary-value">{{ overview?.courses.length || 0 }}</div>
          </el-card>
          <el-card shadow="never" class="summary-card">
            <div class="summary-label">资料完成数</div>
            <div class="summary-value">
              {{ overview?.completed_materials || 0 }}/{{ overview?.total_materials || 0 }}
            </div>
          </el-card>
          <el-card shadow="never" class="summary-card">
            <div class="summary-label">学习进度</div>
            <div class="summary-value">{{ overview?.progress_percent || 0 }}%</div>
          </el-card>
        </div>

        <el-empty
          v-if="!loadingOverview && !overview?.courses.length && !overview?.standalone_contents.length"
          description="当前项目还没有配置培训内容"
        />

        <el-collapse v-else v-model="expandedCourses" class="course-collapse">
          <el-collapse-item
            v-for="course in overview?.courses || []"
            :key="course.id"
            :name="String(course.id)"
          >
            <template #title>
              <div class="course-title-row">
                <div>
                  <div class="course-title">{{ course.title }}</div>
                  <div class="course-summary">{{ course.summary || '暂无课程简介' }}</div>
                </div>
                <div class="course-metrics">
                  <el-tag :type="course.published ? 'success' : 'info'">
                    {{ course.published ? '已发布' : '草稿' }}
                  </el-tag>
                  <span>{{ course.completed_materials }}/{{ course.total_materials }}</span>
                </div>
              </div>
            </template>

            <div v-for="chapter in course.chapters" :key="chapter.id" class="chapter-block">
              <div class="chapter-header">
                <div>
                  <div class="chapter-title">{{ chapter.title }}</div>
                  <div class="chapter-summary">{{ chapter.summary || '暂无章节简介' }}</div>
                </div>
                <div class="chapter-progress">
                  <span>{{ chapter.completed_materials }}/{{ chapter.total_materials }}</span>
                  <el-progress :percentage="chapter.progress_percent" :stroke-width="8" />
                </div>
              </div>

              <el-table :data="chapter.materials" size="small" border>
                <el-table-column prop="title" label="资料" min-width="220" />
                <el-table-column prop="content_type" label="类型" width="110">
                  <template #default="{ row }">
                    <el-tag size="small">{{ contentTypeLabel(row.content_type) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="estimated_minutes" label="预计时长" width="110">
                  <template #default="{ row }">{{ row.estimated_minutes || 0 }} 分钟</template>
                </el-table-column>
                <el-table-column label="状态" width="140">
                  <template #default="{ row }">
                    <el-tag :type="row.learned ? 'success' : 'warning'">
                      {{ row.learned ? '已完成' : '待学习' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="180">
                  <template #default="{ row }">
                    <el-space>
                      <el-button size="small" type="primary" @click="openContent(row)">查看</el-button>
                      <el-button size="small" @click="markContent(row)">
                        {{ row.learned ? '重新记录' : '标记完成' }}
                      </el-button>
                    </el-space>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-collapse-item>
        </el-collapse>

        <el-card
          v-if="overview?.standalone_contents.length"
          shadow="never"
          class="standalone-card"
        >
          <template #header>
            <div class="section-header">未归档资料</div>
          </template>
          <el-table :data="overview?.standalone_contents || []" size="small" border>
            <el-table-column prop="title" label="资料" min-width="220" />
            <el-table-column prop="content_type" label="类型" width="110">
              <template #default="{ row }">
                <el-tag size="small">{{ contentTypeLabel(row.content_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="row.learned ? 'success' : 'warning'">
                  {{ row.learned ? '已完成' : '待学习' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180">
              <template #default="{ row }">
                <el-space>
                  <el-button size="small" type="primary" @click="openContent(row)">查看</el-button>
                  <el-button size="small" @click="markContent(row)">标记完成</el-button>
                </el-space>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="考试中心" name="exam">
        <el-card shadow="never" class="exam-card">
          <template #header>
            <div class="section-header">
              <span>试卷列表</span>
              <el-button text @click="loadExamData">刷新</el-button>
            </div>
          </template>

          <div v-if="currentExam" class="exam-workspace">
            <div class="exam-toolbar">
              <div>
                <div class="exam-name">{{ currentExam.paper_name }}</div>
                <div class="exam-meta">
                  满分 {{ currentExam.total_score }}，及格 {{ currentExam.pass_score }}，时长 {{ currentExam.duration_minutes }} 分钟
                </div>
              </div>
              <div class="exam-status">
                <el-tag type="danger">剩余 {{ timeLeft }} 分钟</el-tag>
                <el-tag type="warning">违规计数 {{ cheatWarnings }}</el-tag>
                <el-button @click="handleSubmitExam">提交考试</el-button>
              </div>
            </div>

            <el-form label-position="top">
              <div
                v-for="(question, index) in currentExam.questions"
                :key="question.id"
                class="question-card"
              >
                <div class="question-title">
                  {{ index + 1 }}. {{ question.question }}（{{ question.score }}分）
                </div>

                <el-radio-group
                  v-if="question.type === 'single'"
                  v-model="examAnswers[question.id]"
                >
                  <el-radio
                    v-for="(opt, idx) in question.options || []"
                    :key="`${question.id}-${idx}`"
                    :value="idx"
                  >
                    {{ opt }}
                  </el-radio>
                </el-radio-group>

                <el-checkbox-group
                  v-else-if="question.type === 'multi'"
                  v-model="examAnswers[question.id]"
                >
                  <el-checkbox
                    v-for="(opt, idx) in question.options || []"
                    :key="`${question.id}-${idx}`"
                    :label="idx"
                  >
                    {{ opt }}
                  </el-checkbox>
                </el-checkbox-group>

                <el-radio-group
                  v-else-if="question.type === 'truefalse'"
                  v-model="examAnswers[question.id]"
                >
                  <el-radio :value="true">正确</el-radio>
                  <el-radio :value="false">错误</el-radio>
                </el-radio-group>

                <el-input
                  v-else-if="question.type === 'fill'"
                  v-model="examAnswers[question.id]"
                  placeholder="请输入答案"
                />

                <el-input
                  v-else
                  v-model="examAnswers[question.id]"
                  type="textarea"
                  :rows="4"
                  placeholder="请输入作答内容"
                />
              </div>
            </el-form>
          </div>

          <template v-else>
            <el-alert
              v-if="examResult"
              :title="examResultText"
              :type="examResult.manual_graded ? (examResult.passed ? 'success' : 'warning') : 'info'"
              show-icon
              class="result-alert"
            />

            <el-row :gutter="16" v-loading="loadingExam">
              <el-col
                v-for="paper in papers"
                :key="paper.id"
                :xs="24"
                :sm="12"
                :lg="8"
              >
                <el-card shadow="hover" class="paper-card">
                  <div class="paper-title-row">
                    <div class="paper-title">{{ paper.name }}</div>
                    <el-tag size="small" :type="paper.published ? 'success' : 'info'">
                      {{ paper.published ? '已发布' : '草稿' }}
                    </el-tag>
                  </div>
                  <div class="paper-desc">{{ paper.description || '暂无试卷说明' }}</div>
                  <div class="paper-metrics">
                    <span>题量 {{ paper.question_count }}</span>
                    <span>满分 {{ paper.total_score }}</span>
                    <span>及格 {{ paper.pass_score }}</span>
                    <span>{{ paper.duration_minutes }} 分钟</span>
                  </div>
                  <el-button
                    type="primary"
                    class="paper-action"
                    :disabled="!paper.published && !authStore.isStaff()"
                    @click="handleStartExam(paper)"
                  >
                    开始考试
                  </el-button>
                </el-card>
              </el-col>
            </el-row>

            <el-empty
              v-if="!loadingExam && !papers.length"
              description="当前项目还没有可用试卷"
            />
          </template>
        </el-card>

        <el-card shadow="never" class="attempt-card">
          <template #header>
            <div class="section-header">我的考试记录</div>
          </template>
          <el-table :data="attempts" size="small" border>
            <el-table-column label="试卷" min-width="220">
              <template #default="{ row }">{{ paperName(row.paper_id) }}</template>
            </el-table-column>
            <el-table-column label="成绩" width="150">
              <template #default="{ row }">
                {{ row.manual_graded ? `${row.score}/${row.total_score}` : '待人工阅卷' }}
              </template>
            </el-table-column>
            <el-table-column label="结果" width="120">
              <template #default="{ row }">
                <el-tag :type="attemptTagType(row)">
                  {{ attemptStatusText(row) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="开始时间" min-width="180">
              <template #default="{ row }">{{ formatDateTime(row.started_at) }}</template>
            </el-table-column>
            <el-table-column label="提交时间" min-width="180">
              <template #default="{ row }">
                {{ row.completed_at ? formatDateTime(row.completed_at) : '进行中' }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane v-if="authStore.isStaff()" label="培训管理" name="admin">
        <div class="admin-shell" v-loading="loadingAdmin">
          <el-card shadow="never" class="admin-hero-card">
            <div class="admin-hero">
              <div class="admin-hero__copy">
                <div class="admin-kicker">Training CMS</div>
                <div class="admin-title">培训内容工作台</div>
                <div class="admin-subtitle">
                  用一套界面完成分类归档、课程编排、章节组织和资料投放。左侧维护结构，中间聚焦课程，右侧处理章节与资料。
                </div>
              </div>
              <div class="admin-hero__actions">
                <el-button type="primary" :icon="Plus" @click="openCourseDialog()">新增课程</el-button>
                <el-button :icon="CollectionTag" @click="openChapterDialog()">新增章节</el-button>
                <el-button :icon="Document" @click="openContentDialog()">新增资料</el-button>
                <el-button :icon="RefreshRight" @click="loadAdminData">刷新数据</el-button>
              </div>
            </div>

            <div class="admin-stat-grid">
              <div
                v-for="metric in adminMetrics"
                :key="metric.key"
                :class="['admin-stat-card', `admin-stat-card--${metric.key}`]"
              >
                <div class="admin-stat-card__label">{{ metric.label }}</div>
                <div class="admin-stat-card__value">{{ metric.value }}</div>
                <div class="admin-stat-card__hint">{{ metric.hint }}</div>
              </div>
            </div>
          </el-card>

          <el-row :gutter="18" class="admin-grid">
            <el-col :xs="24" :xl="6" :lg="8">
              <el-card shadow="never" class="workspace-card workspace-card--taxonomy">
                <template #header>
                  <div class="workspace-card__header">
                    <div>
                      <div class="workspace-chip">Taxonomy</div>
                      <div class="workspace-title">分类管理</div>
                    </div>
                    <el-tag effect="plain" round>{{ categories.length }} 项</el-tag>
                  </div>
                </template>

                <div class="workspace-intro">分类决定课程导航与运营标签，适合先搭出一级结构再继续分配课程。</div>

                <div class="quick-create-row">
                  <el-input v-model="newCategoryName" placeholder="新增分类名称" />
                  <el-button type="primary" :icon="Plus" @click="addCategory">新增</el-button>
                </div>

                <el-scrollbar max-height="560px" class="entity-scroll">
                  <div v-if="categories.length" class="entity-stack">
                    <div v-for="category in categories" :key="category.id" class="entity-card entity-card--compact">
                      <div class="entity-card__main">
                        <div class="entity-card__title-row">
                          <div class="entity-card__title">{{ category.name }}</div>
                          <el-tag size="small" effect="plain">
                            {{ getCategoryCourseCount(category.id) }} 门课程
                          </el-tag>
                        </div>
                        <div class="entity-card__meta">用于课程聚类、搜索筛选和运营归档</div>
                      </div>
                      <div class="entity-card__actions">
                        <el-button text size="small" @click="editCategory(category)">编辑</el-button>
                        <el-button text size="small" type="danger" @click="removeCategory(category)">删除</el-button>
                      </div>
                    </div>
                  </div>
                  <el-empty v-else description="暂无分类" />
                </el-scrollbar>
              </el-card>
            </el-col>

            <el-col :xs="24" :xl="7" :lg="8">
              <el-card shadow="never" class="workspace-card workspace-card--course">
                <template #header>
                  <div class="workspace-card__header">
                    <div>
                      <div class="workspace-chip">Courses</div>
                      <div class="workspace-title">课程编排</div>
                    </div>
                    <el-tag effect="plain" round>{{ courses.length }} 门</el-tag>
                  </div>
                </template>

                <div class="workspace-intro">点击课程即可切换右侧工作区焦点。当前选中项会高亮，便于连续维护章节和资料。</div>

                <el-scrollbar max-height="640px" class="entity-scroll">
                  <div v-if="courses.length" class="entity-stack">
                    <div
                      v-for="course in courses"
                      :key="course.id"
                      :class="['entity-card', 'entity-card--interactive', { 'is-active': selectedCourseId === course.id }]"
                      @click="selectCourse(course.id)"
                    >
                      <div class="entity-card__eyebrow">
                        <el-tag size="small" :type="course.published ? 'success' : 'info'" effect="plain">
                          {{ course.published ? '已发布' : '草稿' }}
                        </el-tag>
                        <span class="entity-card__order">排序 {{ course.sort_order }}</span>
                      </div>
                      <div class="entity-card__title">{{ course.title }}</div>
                      <div class="entity-card__meta">{{ categoryName(course.category_id) }}</div>
                      <div class="entity-card__description">
                        {{ course.summary || '暂无课程简介，建议补充学习目标与适用对象。' }}
                      </div>
                      <div class="entity-card__stat-row">
                        <div class="entity-mini-stat">
                          <span class="entity-mini-stat__label">章节</span>
                          <span class="entity-mini-stat__value">{{ getCourseChapterCount(course.id) }}</span>
                        </div>
                        <div class="entity-mini-stat">
                          <span class="entity-mini-stat__label">资料</span>
                          <span class="entity-mini-stat__value">{{ getCourseMaterialCount(course.id) }}</span>
                        </div>
                      </div>
                      <div class="entity-card__actions entity-card__actions--inline">
                        <el-button text size="small" @click.stop="selectCourse(course.id)">设为焦点</el-button>
                        <el-button text size="small" @click.stop="openCourseDialog(course)">编辑</el-button>
                        <el-button text size="small" type="danger" @click.stop="removeCourse(course)">删除</el-button>
                      </div>
                    </div>
                  </div>
                  <el-empty v-else description="暂无课程" />
                </el-scrollbar>
              </el-card>
            </el-col>

            <el-col :xs="24" :xl="11" :lg="8">
              <el-card shadow="never" class="workspace-card workspace-card--content">
                <template #header>
                  <div class="workspace-card__header workspace-card__header--stack">
                    <div>
                      <div class="workspace-chip">Structure</div>
                      <div class="workspace-title">章节与资料工作区</div>
                    </div>
                    <div class="header-actions">
                      <el-button text @click="clearAdminFocus">清空焦点</el-button>
                      <el-button :icon="CollectionTag" @click="openChapterDialog()">新增章节</el-button>
                      <el-button type="primary" :icon="Document" @click="openContentDialog()">新增资料</el-button>
                    </div>
                  </div>
                </template>

                <div class="focus-grid">
                  <div class="focus-card">
                    <div class="focus-card__label">当前课程</div>
                    <div class="focus-card__value">{{ selectedCourse?.title || '全部课程' }}</div>
                    <div class="focus-card__hint">
                      {{ selectedCourse ? `${getCourseChapterCount(selectedCourse.id)} 章节 / ${getCourseMaterialCount(selectedCourse.id)} 资料` : '未限制课程范围' }}
                    </div>
                  </div>
                  <div class="focus-card focus-card--subtle">
                    <div class="focus-card__label">当前章节</div>
                    <div class="focus-card__value">{{ selectedChapter?.title || '全部章节' }}</div>
                    <div class="focus-card__hint">
                      {{ selectedChapter ? `${getChapterMaterialCount(selectedChapter.id)} 份资料` : '显示所选范围内全部章节资料' }}
                    </div>
                  </div>
                </div>

                <div class="admin-filter-bar">
                  <el-select v-model="selectedCourseId" clearable placeholder="按课程筛选" class="admin-filter-select">
                    <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.id" />
                  </el-select>
                  <el-select v-model="selectedChapterId" clearable placeholder="按章节筛选" class="admin-filter-select">
                    <el-option
                      v-for="chapter in filteredChapterOptions"
                      :key="chapter.id"
                      :label="chapter.title"
                      :value="chapter.id"
                    />
                  </el-select>
                </div>

                <div class="subsection-head">
                  <div>
                    <div class="subsection-head__title">章节带</div>
                    <div class="subsection-head__hint">先选章节，再下方维护资料会更精确。</div>
                  </div>
                  <el-tag effect="plain" round>{{ filteredChapters.length }} 个章节</el-tag>
                </div>

                <div v-if="filteredChapters.length" class="chapter-lane">
                  <div
                    v-for="chapter in filteredChapters"
                    :key="chapter.id"
                    :class="['chapter-card', { 'is-active': selectedChapterId === chapter.id }]"
                    @click="selectChapter(chapter.id)"
                  >
                    <div class="chapter-card__head">
                      <div class="chapter-card__title">{{ chapter.title }}</div>
                      <el-tag size="small" :type="chapter.published ? 'success' : 'info'" effect="plain">
                        {{ chapter.published ? '已发布' : '草稿' }}
                      </el-tag>
                    </div>
                    <div class="chapter-card__meta">
                      <span>{{ courseName(chapter.course_id) }}</span>
                      <span>{{ getChapterMaterialCount(chapter.id) }} 资料</span>
                    </div>
                    <div class="chapter-card__summary">
                      {{ chapter.summary || '暂无章节简介，可补充本章节学习目标。' }}
                    </div>
                    <div class="chapter-card__actions">
                      <el-button text size="small" @click.stop="selectChapter(chapter.id)">聚焦</el-button>
                      <el-button text size="small" @click.stop="openChapterDialog(chapter)">编辑</el-button>
                      <el-button text size="small" type="danger" @click.stop="removeChapter(chapter)">删除</el-button>
                    </div>
                  </div>
                </div>
                <el-empty v-else description="当前筛选范围下没有章节" />

                <div class="subsection-head subsection-head--materials">
                  <div>
                    <div class="subsection-head__title">资料列表</div>
                    <div class="subsection-head__hint">{{ materialPanelHint }}</div>
                  </div>
                  <el-tag effect="plain" round>{{ filteredContents.length }} 份资料</el-tag>
                </div>

                <el-table
                  :data="filteredContents"
                  size="small"
                  border
                  class="admin-table admin-table--materials"
                >
                  <el-table-column label="资料信息" min-width="250">
                    <template #default="{ row }">
                      <div class="material-cell">
                        <div class="material-cell__title">{{ row.title }}</div>
                        <div class="material-cell__description">{{ row.description || '暂无资料简介' }}</div>
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="章节" min-width="150">
                    <template #default="{ row }">
                      {{ chapterName(row.chapter_id) }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="content_type" label="类型" width="110">
                    <template #default="{ row }">
                      <el-tag size="small" effect="plain">{{ contentTypeLabel(row.content_type) }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="时长" width="100">
                    <template #default="{ row }">{{ row.estimated_minutes || 0 }} 分钟</template>
                  </el-table-column>
                  <el-table-column label="状态" width="100">
                    <template #default="{ row }">
                      <el-tag size="small" :type="row.published ? 'success' : 'info'">
                        {{ row.published ? '已发布' : '草稿' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" width="150" fixed="right">
                    <template #default="{ row }">
                      <el-space>
                        <el-button size="small" @click="openContentDialog(row)">编辑</el-button>
                        <el-button size="small" type="danger" @click="removeContent(row)">删除</el-button>
                      </el-space>
                    </template>
                  </el-table-column>
                </el-table>
              </el-card>
            </el-col>
          </el-row>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="courseDialogVisible" :title="courseDialogTitle" width="640px">
      <el-form :model="courseForm" label-width="100px">
        <el-form-item label="课程标题">
          <el-input v-model="courseForm.title" />
        </el-form-item>
        <el-form-item label="课程简介">
          <el-input v-model="courseForm.summary" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="所属分类">
          <el-select v-model="courseForm.category_id" clearable placeholder="可选">
            <el-option v-for="category in categories" :key="category.id" :label="category.name" :value="category.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="封面链接">
          <el-input v-model="courseForm.cover_url" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="courseForm.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="发布">
          <el-switch v-model="courseForm.published" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="courseDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCourse">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="chapterDialogVisible" :title="chapterDialogTitle" width="640px">
      <el-form :model="chapterForm" label-width="100px">
        <el-form-item label="所属课程">
          <el-select v-model="chapterForm.course_id" placeholder="请选择课程">
            <el-option v-for="course in courses" :key="course.id" :label="course.title" :value="course.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="章节标题">
          <el-input v-model="chapterForm.title" />
        </el-form-item>
        <el-form-item label="章节简介">
          <el-input v-model="chapterForm.summary" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="chapterForm.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="发布">
          <el-switch v-model="chapterForm.published" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="chapterDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveChapter">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="contentDialogVisible" :title="contentDialogTitle" width="680px">
      <el-form :model="contentForm" label-width="110px">
        <el-form-item label="资料标题">
          <el-input v-model="contentForm.title" />
        </el-form-item>
        <el-form-item label="资料简介">
          <el-input v-model="contentForm.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="所属章节">
          <el-select v-model="contentForm.chapter_id" clearable placeholder="可为空">
            <el-option
              v-for="chapter in filteredChapterOptionsForContent"
              :key="chapter.id"
              :label="chapter.title"
              :value="chapter.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="所属分类">
          <el-select v-model="contentForm.category_id" clearable placeholder="可选">
            <el-option v-for="category in categories" :key="category.id" :label="category.name" :value="category.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="资料类型">
          <el-select v-model="contentForm.content_type">
            <el-option label="链接" value="link" />
            <el-option label="文档" value="document" />
            <el-option label="视频" value="video" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="contentForm.content_type === 'link'" label="资料链接">
          <el-input v-model="contentForm.file_url" placeholder="请输入外部链接或系统内地址" />
        </el-form-item>
        <el-form-item v-else label="上传文件">
          <div class="content-upload-panel">
            <el-upload
              class="content-upload-box"
              drag
              :auto-upload="false"
              :show-file-list="false"
              :accept="contentUploadAccept"
              :on-change="handleContentFileChange"
              :before-upload="() => false"
            >
              <el-icon class="content-upload-box__icon"><UploadFilled /></el-icon>
              <div class="content-upload-box__title">
                {{ contentForm.content_type === 'document' ? '拖拽或点击上传文档' : '拖拽或点击上传视频' }}
              </div>
              <div class="content-upload-box__hint">{{ contentUploadTip }}</div>
            </el-upload>

            <div v-if="contentUploadList.length" class="content-upload-file">
              <div class="content-upload-file__name">{{ contentUploadList[0].name }}</div>
              <div class="content-upload-file__meta">新文件将在保存资料时自动上传并覆盖旧文件</div>
              <el-button text type="danger" @click="clearPendingContentUpload">移除</el-button>
            </div>

            <div v-else-if="contentForm.file_url" class="content-upload-file content-upload-file--existing">
              <div class="content-upload-file__name">{{ currentContentFileName }}</div>
              <div class="content-upload-file__meta">当前已保存文件</div>
              <el-button text type="primary" @click="openStoredContentFile">打开文件</el-button>
            </div>
          </div>
        </el-form-item>
        <el-form-item label="预计时长">
          <el-input-number v-model="contentForm.estimated_minutes" :min="0" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="contentForm.sort_order" :min="0" />
        </el-form-item>
        <el-form-item label="发布">
          <el-switch v-model="contentForm.published" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="contentDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveContent">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadProps, UploadUserFile } from 'element-plus'
import { CollectionTag, Document, Plus, RefreshRight, UploadFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import {
  createTrainingCategory,
  createTrainingChapter,
  createTrainingContent,
  createTrainingCourse,
  deleteTrainingCategory,
  deleteTrainingChapter,
  deleteTrainingContent,
  deleteTrainingCourse,
  getTrainingCategories,
  getTrainingChapters,
  getTrainingContents,
  getTrainingCourses,
  getTrainingOverview,
  markTrainingRecord,
  uploadTrainingContentFile,
  updateTrainingCategory,
  updateTrainingChapter,
  updateTrainingContent,
  updateTrainingCourse,
} from '@/api/training'
import { getExamAttempts, getExamPapers, startExamPaper, submitExamPaper } from '@/api/exams'
import type {
  ExamAttemptSummary,
  ExamPaper,
  ExamQuestion,
  ExamStartResponse,
  TrainingCategory,
  TrainingChapter,
  TrainingContent,
  TrainingContentProgress,
  TrainingCourse,
  TrainingOverview,
} from '@/types'
import { formatDateTime } from '@/utils/helpers'

const authStore = useAuthStore()
const router = useRouter()

const activeTab = ref('learning')
const expandedCourses = ref<string[]>([])

const loadingOverview = ref(false)
const loadingExam = ref(false)
const loadingAdmin = ref(false)

const overview = ref<TrainingOverview | null>(null)
const papers = ref<ExamPaper[]>([])
const attempts = ref<ExamAttemptSummary[]>([])
const currentExam = ref<ExamStartResponse | null>(null)
const examResult = ref<ExamAttemptSummary | null>(null)
const timeLeft = ref(0)
const cheatWarnings = ref(0)
const examAnswers = reactive<Record<number, any>>({})
let examTimer: number | null = null

const categories = ref<TrainingCategory[]>([])
const courses = ref<TrainingCourse[]>([])
const chapters = ref<TrainingChapter[]>([])
const contents = ref<TrainingContent[]>([])
const selectedCourseId = ref<number | null>(null)
const selectedChapterId = ref<number | null>(null)

const newCategoryName = ref('')

const courseDialogVisible = ref(false)
const chapterDialogVisible = ref(false)
const contentDialogVisible = ref(false)
const courseDialogTitle = ref('新增课程')
const chapterDialogTitle = ref('新增章节')
const contentDialogTitle = ref('新增资料')
const pendingContentFile = ref<File | null>(null)
const contentUploadList = ref<UploadUserFile[]>([])

const courseForm = reactive<Partial<TrainingCourse>>({
  id: undefined,
  title: '',
  summary: '',
  cover_url: '',
  category_id: undefined,
  sort_order: 0,
  published: true,
})

const chapterForm = reactive<Partial<TrainingChapter>>({
  id: undefined,
  course_id: undefined,
  title: '',
  summary: '',
  sort_order: 0,
  published: true,
})

const contentForm = reactive<Partial<TrainingContent>>({
  id: undefined,
  title: '',
  description: '',
  file_url: '',
  category_id: undefined,
  chapter_id: undefined,
  content_type: 'link',
  estimated_minutes: 0,
  sort_order: 0,
  published: true,
})

const paperMap = computed(() => {
  const map = new Map<number, ExamPaper>()
  papers.value.forEach((paper) => map.set(paper.id, paper))
  return map
})

const categoryMap = computed(() => {
  const map = new Map<number, TrainingCategory>()
  categories.value.forEach((category) => map.set(category.id, category))
  return map
})

const courseMap = computed(() => {
  const map = new Map<number, TrainingCourse>()
  courses.value.forEach((course) => map.set(course.id, course))
  return map
})

const chapterMap = computed(() => {
  const map = new Map<number, TrainingChapter>()
  chapters.value.forEach((chapter) => map.set(chapter.id, chapter))
  return map
})

const selectedCourse = computed(() => {
  if (!selectedCourseId.value) return null
  return courseMap.value.get(selectedCourseId.value) || null
})

const selectedChapter = computed(() => {
  if (!selectedChapterId.value) return null
  return chapterMap.value.get(selectedChapterId.value) || null
})

const adminMetrics = computed(() => [
  {
    key: 'categories',
    label: '分类',
    value: categories.value.length,
    hint: `${courses.value.filter((course) => course.category_id).length} 门已归类课程`,
  },
  {
    key: 'courses',
    label: '课程',
    value: courses.value.length,
    hint: `${courses.value.filter((course) => course.published).length} 门已发布`,
  },
  {
    key: 'chapters',
    label: '章节',
    value: chapters.value.length,
    hint: `${chapters.value.filter((chapter) => chapter.published).length} 个可见章节`,
  },
  {
    key: 'materials',
    label: '资料',
    value: contents.value.length,
    hint: `${contents.value.filter((content) => content.published).length} 份已发布资料`,
  },
])

const filteredChapterOptions = computed(() => {
  if (!selectedCourseId.value) return chapters.value
  return chapters.value.filter((chapter) => chapter.course_id === selectedCourseId.value)
})

const filteredChapterOptionsForContent = computed(() => {
  if (contentForm.chapter_id) {
    const chapter = chapterMap.value.get(contentForm.chapter_id)
    if (chapter && !filteredChapterOptions.value.find((item) => item.id === chapter.id)) {
      return [...filteredChapterOptions.value, chapter]
    }
  }
  return filteredChapterOptions.value
})

const filteredChapters = computed(() => {
  if (!selectedCourseId.value) return chapters.value
  return chapters.value.filter((chapter) => chapter.course_id === selectedCourseId.value)
})

const filteredContents = computed(() => {
  if (selectedChapterId.value) {
    return contents.value.filter((content) => content.chapter_id === selectedChapterId.value)
  }
  if (selectedCourseId.value) {
    const chapterIds = filteredChapters.value.map((chapter) => chapter.id)
    return contents.value.filter((content) => content.chapter_id && chapterIds.includes(content.chapter_id))
  }
  return contents.value
})

const materialPanelHint = computed(() => {
  if (selectedChapter.value) {
    return `当前聚焦章节“${selectedChapter.value.title}”，下表展示本章节资料。`
  }
  if (selectedCourse.value) {
    return `当前聚焦课程“${selectedCourse.value.title}”，下表展示其全部章节资料。`
  }
  return '当前展示全部资料，可通过上方筛选快速聚焦具体课程或章节。'
})

const contentUploadAccept = computed(() => {
  if (contentForm.content_type === 'document') {
    return '.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.md'
  }
  if (contentForm.content_type === 'video') {
    return '.mp4,.mov,.avi,.mkv,.webm,.m4v'
  }
  return ''
})

const contentUploadTip = computed(() => {
  if (contentForm.content_type === 'document') {
    return '支持 PDF、Word、PPT、Excel、TXT、Markdown，单文件最大 30MB'
  }
  if (contentForm.content_type === 'video') {
    return '支持 MP4、MOV、AVI、MKV、WEBM、M4V，单文件最大 300MB'
  }
  return ''
})

const currentContentFileName = computed(() => {
  if (!contentForm.file_url) return '未上传文件'
  return contentForm.file_url.split('/').pop() || '已上传文件'
})

const examResultText = computed(() => {
  if (!examResult.value) return ''
  if (!examResult.value.manual_graded) {
    return '考试已提交，存在主观题，等待人工阅卷后生成最终成绩'
  }
  return `得分 ${examResult.value.score}/${examResult.value.total_score}，${examResult.value.passed ? '考试合格' : '考试未通过'}`
})

const contentTypeLabel = (contentType: TrainingContent['content_type']) => {
  const mapping: Record<TrainingContent['content_type'], string> = {
    link: '链接',
    document: '文档',
    video: '视频',
  }
  return mapping[contentType]
}

const categoryName = (categoryId?: number) => {
  if (!categoryId) return '未分类'
  return categoryMap.value.get(categoryId)?.name || `分类 #${categoryId}`
}

const courseName = (courseId?: number) => {
  if (!courseId) return '未绑定课程'
  return courseMap.value.get(courseId)?.title || `课程 #${courseId}`
}

const chapterName = (chapterId?: number) => {
  if (!chapterId) return '未归档'
  return chapterMap.value.get(chapterId)?.title || `章节 #${chapterId}`
}

const getCategoryCourseCount = (categoryId: number) => {
  return courses.value.filter((course) => course.category_id === categoryId).length
}

const getCourseChapterCount = (courseId: number) => {
  return chapters.value.filter((chapter) => chapter.course_id === courseId).length
}

const getChapterMaterialCount = (chapterId: number) => {
  return contents.value.filter((content) => content.chapter_id === chapterId).length
}

const getCourseMaterialCount = (courseId: number) => {
  const chapterIds = chapters.value
    .filter((chapter) => chapter.course_id === courseId)
    .map((chapter) => chapter.id)
  return contents.value.filter((content) => content.chapter_id && chapterIds.includes(content.chapter_id)).length
}

const paperName = (paperId?: number) => {
  if (!paperId) return '未绑定试卷'
  return paperMap.value.get(paperId)?.name || `试卷 #${paperId}`
}

const attemptStatusText = (attempt: ExamAttemptSummary) => {
  if (!attempt.completed_at) return '进行中'
  if (!attempt.manual_graded) return '待人工阅卷'
  return attempt.passed ? '已通过' : '未通过'
}

const attemptTagType = (attempt: ExamAttemptSummary) => {
  if (!attempt.completed_at) return 'info'
  if (!attempt.manual_graded) return 'warning'
  return attempt.passed ? 'success' : 'danger'
}

const clearExamTimer = () => {
  if (examTimer) {
    clearInterval(examTimer)
    examTimer = null
  }
}

const resetExamWorkspace = () => {
  currentExam.value = null
  clearExamTimer()
  Object.keys(examAnswers).forEach((key) => delete examAnswers[Number(key)])
}

const startCountdown = (minutes: number) => {
  clearExamTimer()
  timeLeft.value = minutes
  examTimer = window.setInterval(() => {
    if (timeLeft.value > 0) {
      timeLeft.value -= 1
      return
    }
    clearExamTimer()
  }, 60000)
}

const loadOverview = async () => {
  loadingOverview.value = true
  try {
    overview.value = await getTrainingOverview({
      include_unpublished: authStore.isStaff(),
    })
    expandedCourses.value = (overview.value?.courses || []).slice(0, 2).map((course) => String(course.id))
  } catch (error) {
    console.error(error)
    ElMessage.error('加载培训中心失败')
  } finally {
    loadingOverview.value = false
  }
}

const loadExamData = async () => {
  loadingExam.value = true
  try {
    const [paperList, attemptList] = await Promise.all([
      getExamPapers(),
      getExamAttempts(),
    ])
    papers.value = paperList
    attempts.value = attemptList
  } catch (error) {
    console.error(error)
    ElMessage.error('加载考试中心失败')
  } finally {
    loadingExam.value = false
  }
}

const loadAdminData = async () => {
  if (!authStore.isStaff()) return
  loadingAdmin.value = true
  try {
    const [categoryList, courseList, chapterList, contentList] = await Promise.all([
      getTrainingCategories(),
      getTrainingCourses({ include_unpublished: true }),
      getTrainingChapters({ include_unpublished: true }),
      getTrainingContents({ include_unpublished: true }),
    ])
    categories.value = categoryList
    courses.value = courseList
    chapters.value = chapterList
    contents.value = contentList
  } catch (error) {
    console.error(error)
    ElMessage.error('加载培训管理数据失败')
  } finally {
    loadingAdmin.value = false
  }
}

const reloadAll = async () => {
  await Promise.all([
    loadOverview(),
    loadExamData(),
    loadAdminData(),
  ])
}

const openContent = (content: TrainingContent | TrainingContentProgress) => {
  router.push(`/training/contents/${content.id}`)
}

const markContent = async (content: TrainingContent | TrainingContentProgress) => {
  try {
    await markTrainingRecord({ content_id: content.id })
    ElMessage.success('已记录学习进度')
    await loadOverview()
  } catch (error) {
    console.error(error)
    ElMessage.error('记录学习进度失败')
  }
}

const handleStartExam = async (paper: ExamPaper) => {
  try {
    const response = await startExamPaper(paper.id)
    currentExam.value = response
    examResult.value = null
    cheatWarnings.value = 0
    Object.keys(examAnswers).forEach((key) => delete examAnswers[Number(key)])
    startCountdown(response.remaining_minutes ?? response.duration_minutes)
  } catch (error) {
    console.error(error)
    ElMessage.error('开始考试失败')
  }
}

const handleSubmitExam = async () => {
  if (!currentExam.value) return
  try {
    const payload = currentExam.value.questions.map((question: ExamQuestion) => ({
      question_id: question.id,
      answer: examAnswers[question.id] ?? null,
    }))
    examResult.value = await submitExamPaper(currentExam.value.attempt_id, {
      answers: payload,
    })
    resetExamWorkspace()
    await loadExamData()
    if (examResult.value.manual_graded) {
      ElMessage.success('考试提交成功')
    } else {
      ElMessage.success('已提交，等待人工阅卷')
    }
  } catch (error) {
    console.error(error)
    ElMessage.error('提交考试失败')
  }
}

const handleVisibilityChange = () => {
  if (!currentExam.value || !document.hidden) return
  cheatWarnings.value += 1
  ElMessage.warning('检测到切换标签页，请保持考试页面前台')
}

const selectCourse = (courseId: number) => {
  selectedCourseId.value = courseId
}

const selectChapter = (chapterId: number) => {
  selectedChapterId.value = chapterId
  const chapter = chapterMap.value.get(chapterId)
  if (chapter) {
    selectedCourseId.value = chapter.course_id
  }
}

const clearAdminFocus = () => {
  selectedCourseId.value = null
  selectedChapterId.value = null
}

const clearPendingContentUpload = () => {
  pendingContentFile.value = null
  contentUploadList.value = []
}

const isAllowedContentFile = (file: File) => {
  const extension = `.${file.name.split('.').pop()?.toLowerCase() || ''}`
  const documentExtensions = new Set(['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.txt', '.md'])
  const videoExtensions = new Set(['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'])

  if (contentForm.content_type === 'document') {
    return documentExtensions.has(extension)
  }
  if (contentForm.content_type === 'video') {
    return videoExtensions.has(extension)
  }
  return false
}

const handleContentFileChange: UploadProps['onChange'] = (uploadFile) => {
  const raw = uploadFile.raw
  if (!raw) return
  if (!isAllowedContentFile(raw)) {
    ElMessage.warning(
      contentForm.content_type === 'document'
        ? '仅支持 PDF、Word、PPT、Excel、TXT、Markdown 文档'
        : '仅支持 MP4、MOV、AVI、MKV、WEBM、M4V 视频',
    )
    clearPendingContentUpload()
    return
  }
  pendingContentFile.value = raw
  contentUploadList.value = [{ name: raw.name, size: raw.size, status: 'ready' }]
}

const openStoredContentFile = () => {
  if (!contentForm.file_url) return
  window.open(contentForm.file_url, '_blank')
}

const addCategory = async () => {
  if (!newCategoryName.value.trim()) {
    ElMessage.warning('请输入分类名称')
    return
  }
  try {
    await createTrainingCategory({ name: newCategoryName.value.trim() })
    newCategoryName.value = ''
    await loadAdminData()
    ElMessage.success('分类创建成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('分类创建失败')
  }
}

const editCategory = async (row: TrainingCategory) => {
  try {
    const result = await ElMessageBox.prompt('请输入新的分类名称', '编辑分类', {
      inputValue: row.name,
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    })
    await updateTrainingCategory(row.id, { name: result.value })
    await loadAdminData()
    ElMessage.success('分类更新成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('分类更新失败')
    }
  }
}

const removeCategory = async (row: TrainingCategory) => {
  try {
    await ElMessageBox.confirm(`确认删除分类“${row.name}”？`, '删除分类', {
      type: 'warning',
    })
    await deleteTrainingCategory(row.id)
    await loadAdminData()
    ElMessage.success('分类已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('分类删除失败')
    }
  }
}

const openCourseDialog = (course?: TrainingCourse) => {
  courseDialogTitle.value = course ? '编辑课程' : '新增课程'
  Object.assign(courseForm, {
    id: course?.id,
    title: course?.title || '',
    summary: course?.summary || '',
    cover_url: course?.cover_url || '',
    category_id: course?.category_id,
    sort_order: course?.sort_order || 0,
    published: course?.published ?? true,
  })
  courseDialogVisible.value = true
}

const saveCourse = async () => {
  if (!courseForm.title?.trim()) {
    ElMessage.warning('请输入课程标题')
    return
  }
  try {
    if (courseForm.id) {
      await updateTrainingCourse(courseForm.id, courseForm)
    } else {
      await createTrainingCourse(courseForm)
    }
    courseDialogVisible.value = false
    await Promise.all([loadOverview(), loadAdminData()])
    ElMessage.success('课程保存成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('课程保存失败')
  }
}

const removeCourse = async (course: TrainingCourse) => {
  try {
    await ElMessageBox.confirm(`确认删除课程“${course.title}”？`, '删除课程', {
      type: 'warning',
    })
    await deleteTrainingCourse(course.id)
    if (selectedCourseId.value === course.id) {
      selectedCourseId.value = null
      selectedChapterId.value = null
    }
    await Promise.all([loadOverview(), loadAdminData()])
    ElMessage.success('课程已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('课程删除失败')
    }
  }
}

const openChapterDialog = (chapter?: TrainingChapter) => {
  chapterDialogTitle.value = chapter ? '编辑章节' : '新增章节'
  Object.assign(chapterForm, {
    id: chapter?.id,
    course_id: chapter?.course_id || selectedCourseId.value || undefined,
    title: chapter?.title || '',
    summary: chapter?.summary || '',
    sort_order: chapter?.sort_order || 0,
    published: chapter?.published ?? true,
  })
  chapterDialogVisible.value = true
}

const saveChapter = async () => {
  if (!chapterForm.course_id) {
    ElMessage.warning('请选择所属课程')
    return
  }
  if (!chapterForm.title?.trim()) {
    ElMessage.warning('请输入章节标题')
    return
  }
  try {
    if (chapterForm.id) {
      await updateTrainingChapter(chapterForm.id, chapterForm)
    } else {
      await createTrainingChapter(chapterForm)
    }
    chapterDialogVisible.value = false
    await Promise.all([loadOverview(), loadAdminData()])
    ElMessage.success('章节保存成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('章节保存失败')
  }
}

const removeChapter = async (chapter: TrainingChapter) => {
  try {
    await ElMessageBox.confirm(`确认删除章节“${chapter.title}”？`, '删除章节', {
      type: 'warning',
    })
    await deleteTrainingChapter(chapter.id)
    if (selectedChapterId.value === chapter.id) {
      selectedChapterId.value = null
    }
    await Promise.all([loadOverview(), loadAdminData()])
    ElMessage.success('章节已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('章节删除失败')
    }
  }
}

const openContentDialog = (content?: TrainingContent) => {
  contentDialogTitle.value = content ? '编辑资料' : '新增资料'
  clearPendingContentUpload()
  Object.assign(contentForm, {
    id: content?.id,
    title: content?.title || '',
    description: content?.description || '',
    file_url: content?.file_url || '',
    category_id: content?.category_id,
    chapter_id: content?.chapter_id,
    content_type: content?.content_type || 'link',
    estimated_minutes: content?.estimated_minutes || 0,
    sort_order: content?.sort_order || 0,
    published: content?.published ?? true,
  })
  if (!content && selectedChapterId.value) {
    contentForm.chapter_id = selectedChapterId.value
  }
  contentDialogVisible.value = true
}

const saveContent = async () => {
  if (!contentForm.title?.trim()) {
    ElMessage.warning('请输入资料标题')
    return
  }
  if (contentForm.content_type === 'link' && !contentForm.file_url?.trim()) {
    ElMessage.warning('链接类型资料必须填写资料链接')
    return
  }
  if (
    contentForm.content_type !== 'link' &&
    !pendingContentFile.value &&
    !contentForm.file_url
  ) {
    ElMessage.warning(contentForm.content_type === 'document' ? '请先上传文档文件' : '请先上传视频文件')
    return
  }

  try {
    const payload = {
      ...contentForm,
      file_url: contentForm.content_type === 'link' ? contentForm.file_url : contentForm.file_url || '',
    }

    let savedContent: TrainingContent
    if (contentForm.id) {
      savedContent = await updateTrainingContent(contentForm.id, payload)
    } else {
      savedContent = await createTrainingContent(payload)
      contentForm.id = savedContent.id
    }

    if (contentForm.content_type !== 'link' && pendingContentFile.value) {
      savedContent = await uploadTrainingContentFile(savedContent.id, pendingContentFile.value)
      contentForm.file_url = savedContent.file_url
      clearPendingContentUpload()
    }
    contentDialogVisible.value = false
    await Promise.all([loadOverview(), loadAdminData()])
    ElMessage.success('资料保存成功')
  } catch (error) {
    console.error(error)
    ElMessage.error('资料保存失败')
  }
}

const removeContent = async (content: TrainingContent) => {
  try {
    await ElMessageBox.confirm(`确认删除资料“${content.title}”？`, '删除资料', {
      type: 'warning',
    })
    await deleteTrainingContent(content.id)
    await Promise.all([loadOverview(), loadAdminData()])
    ElMessage.success('资料已删除')
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
      ElMessage.error('资料删除失败')
    }
  }
}

watch(selectedCourseId, (courseId) => {
  if (!courseId) {
    selectedChapterId.value = null
    return
  }
  const chapter = selectedChapterId.value
    ? chapterMap.value.get(selectedChapterId.value)
    : null
  if (chapter && chapter.course_id !== courseId) {
    selectedChapterId.value = null
  }
})

onMounted(async () => {
  await reloadAll()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', handleVisibilityChange)
  clearExamTimer()
})
</script>

<style scoped>
.page-container {
  padding: 20px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.summary-card {
  border-radius: 14px;
}

.summary-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.summary-value {
  margin-top: 10px;
  font-size: 28px;
  font-weight: 700;
}

.course-collapse {
  margin-top: 8px;
}

.course-title-row,
.chapter-header,
.section-header,
.paper-title-row,
.exam-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.course-title,
.paper-title,
.chapter-title,
.exam-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.course-summary,
.chapter-summary,
.paper-desc,
.exam-meta {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.course-metrics,
.paper-metrics,
.exam-status {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.chapter-block + .chapter-block {
  margin-top: 18px;
}

.chapter-progress {
  min-width: 220px;
}

.standalone-card,
.attempt-card,
.exam-card {
  margin-top: 16px;
}

.paper-card {
  margin-bottom: 16px;
  min-height: 220px;
}

.paper-action {
  margin-top: 16px;
  width: 100%;
}

.result-alert {
  margin-bottom: 16px;
}

.exam-workspace {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.question-card {
  border: 1px solid var(--el-border-color-light);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  background: #fff;
}

.question-title {
  margin-bottom: 12px;
  font-weight: 600;
  line-height: 1.7;
}

.admin-shell {
  --admin-ink: #14324a;
  --admin-accent: #216b72;
  --admin-accent-soft: #e8f6f4;
  --admin-warm: #d58f2c;
  --admin-border: #d8e4ea;
  --admin-surface: #fbfdfe;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.admin-hero-card {
  margin-bottom: 0;
  border: none;
  border-radius: 26px;
  overflow: hidden;
  background:
    radial-gradient(circle at top right, rgba(255, 217, 137, 0.24), transparent 32%),
    linear-gradient(135deg, #12344c 0%, #1f6870 54%, #2c8b83 100%);
}

.admin-hero-card :deep(.el-card__body) {
  padding: 24px;
}

.admin-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 18px;
}

.admin-hero__copy {
  max-width: 760px;
  color: #fff;
}

.admin-kicker {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.admin-title {
  margin-top: 14px;
  font-size: 30px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.admin-subtitle {
  margin-top: 12px;
  max-width: 680px;
  line-height: 1.75;
  color: rgba(255, 255, 255, 0.84);
}

.admin-hero__actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.admin-stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-top: 24px;
}

.admin-stat-card {
  padding: 16px 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.28);
  box-shadow: 0 18px 40px rgba(10, 31, 45, 0.12);
}

.admin-stat-card__label {
  font-size: 12px;
  font-weight: 600;
  color: rgba(20, 50, 74, 0.66);
}

.admin-stat-card__value {
  margin-top: 10px;
  font-size: 28px;
  font-weight: 700;
  color: var(--admin-ink);
}

.admin-stat-card__hint {
  margin-top: 6px;
  font-size: 13px;
  color: #567082;
}

.admin-stat-card--materials {
  background: linear-gradient(180deg, #fffaf1 0%, #ffffff 100%);
}

.admin-grid {
  margin-top: 0;
}

.workspace-card {
  height: 100%;
  margin-bottom: 0;
  border-radius: 24px;
  border: 1px solid var(--admin-border);
  background: linear-gradient(180deg, #ffffff 0%, var(--admin-surface) 100%);
  box-shadow: 0 10px 30px rgba(15, 37, 54, 0.06);
}

.workspace-card :deep(.el-card__header) {
  padding: 20px 22px 0;
  border-bottom: none;
}

.workspace-card :deep(.el-card__body) {
  padding: 18px 22px 22px;
}

.workspace-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.workspace-card__header--stack {
  align-items: flex-start;
}

.workspace-chip {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--admin-accent-soft);
  color: var(--admin-accent);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.workspace-title {
  margin-top: 10px;
  font-size: 20px;
  font-weight: 700;
  color: var(--admin-ink);
}

.workspace-intro {
  margin-bottom: 18px;
  color: #5d7484;
  line-height: 1.7;
}

.quick-create-row {
  display: flex;
  gap: 10px;
  margin-bottom: 18px;
}

.entity-scroll :deep(.el-scrollbar__view) {
  display: block;
}

.entity-stack {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.entity-card,
.chapter-card,
.focus-card {
  border: 1px solid var(--admin-border);
  border-radius: 18px;
  background: #fff;
}

.entity-card {
  padding: 14px 16px;
}

.entity-card--compact {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 14px;
}

.entity-card--interactive {
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.entity-card--interactive:hover,
.chapter-card:hover {
  transform: translateY(-2px);
  border-color: #bed3dc;
  box-shadow: 0 14px 28px rgba(17, 50, 73, 0.08);
}

.entity-card--interactive.is-active,
.chapter-card.is-active {
  border-color: var(--admin-accent);
  box-shadow: 0 16px 34px rgba(33, 107, 114, 0.14);
  background: linear-gradient(180deg, #ffffff 0%, #f3fbfa 100%);
}

.entity-card__main {
  min-width: 0;
  flex: 1;
}

.entity-card__eyebrow,
.entity-card__title-row,
.entity-card__actions,
.chapter-card__head,
.chapter-card__meta,
.chapter-card__actions,
.focus-grid,
.admin-filter-bar,
.subsection-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.entity-card__eyebrow,
.chapter-card__meta {
  justify-content: space-between;
}

.entity-card__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--admin-ink);
  line-height: 1.4;
}

.entity-card__meta,
.entity-card__description,
.chapter-card__summary,
.focus-card__hint,
.subsection-head__hint,
.material-cell__description {
  color: #627987;
  line-height: 1.6;
}

.entity-card__meta {
  margin-top: 6px;
  font-size: 13px;
}

.entity-card__description {
  margin-top: 10px;
  font-size: 13px;
}

.entity-card__order {
  font-size: 12px;
  color: #6d8593;
}

.entity-card__stat-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.entity-mini-stat {
  padding: 10px 12px;
  border-radius: 14px;
  background: #f6fafc;
}

.entity-mini-stat__label {
  display: block;
  font-size: 12px;
  color: #68808f;
}

.entity-mini-stat__value {
  display: block;
  margin-top: 4px;
  font-size: 18px;
  font-weight: 700;
  color: var(--admin-ink);
}

.entity-card__actions {
  margin-top: 12px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.entity-card__actions--inline {
  margin-top: 14px;
}

.focus-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.focus-card {
  padding: 16px 18px;
  background: linear-gradient(180deg, #f8fbfc 0%, #ffffff 100%);
}

.focus-card--subtle {
  background: linear-gradient(180deg, #fff9f1 0%, #ffffff 100%);
}

.focus-card__label {
  font-size: 12px;
  font-weight: 700;
  color: #6a8091;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.focus-card__value {
  margin-top: 10px;
  font-size: 20px;
  font-weight: 700;
  color: var(--admin-ink);
}

.focus-card__hint {
  margin-top: 6px;
  font-size: 13px;
}

.admin-filter-bar {
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.admin-filter-select {
  width: 220px;
}

.subsection-head {
  justify-content: space-between;
  margin: 18px 0 12px;
}

.subsection-head--materials {
  margin-top: 22px;
}

.subsection-head__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--admin-ink);
}

.subsection-head__hint {
  margin-top: 4px;
  font-size: 13px;
}

.chapter-lane {
  display: grid;
  gap: 12px;
}

.chapter-card {
  padding: 14px 16px;
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.chapter-card__head {
  justify-content: space-between;
  align-items: flex-start;
}

.chapter-card__title {
  font-size: 15px;
  font-weight: 700;
  color: var(--admin-ink);
}

.chapter-card__meta {
  margin-top: 8px;
  font-size: 12px;
  color: #6e8594;
}

.chapter-card__summary {
  margin-top: 10px;
  font-size: 13px;
}

.chapter-card__actions {
  margin-top: 12px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.admin-table {
  margin-top: 0;
}

.admin-table :deep(th.el-table__cell) {
  background: #f4f8fa;
  color: #486273;
  font-weight: 700;
}

.admin-table--materials :deep(.el-table__row:hover > td.el-table__cell) {
  background: #f7fbfc;
}

.material-cell__title {
  font-size: 14px;
  font-weight: 700;
  color: var(--admin-ink);
}

.material-cell__description {
  margin-top: 4px;
  font-size: 12px;
}

.content-upload-panel {
  width: 100%;
}

.content-upload-box {
  width: 100%;
}

.content-upload-box :deep(.el-upload) {
  width: 100%;
}

.content-upload-box :deep(.el-upload-dragger) {
  width: 100%;
  padding: 26px 18px;
  border-radius: 18px;
  border-color: #bdd2dd;
  background: linear-gradient(180deg, #f8fbfc 0%, #ffffff 100%);
}

.content-upload-box__icon {
  font-size: 30px;
  color: var(--admin-accent);
}

.content-upload-box__title {
  margin-top: 10px;
  font-size: 15px;
  font-weight: 700;
  color: var(--admin-ink);
}

.content-upload-box__hint {
  margin-top: 6px;
  font-size: 13px;
  color: #6b8391;
}

.content-upload-file {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #f6fafc;
  border: 1px solid #dbe6ec;
}

.content-upload-file--existing {
  background: #fffaf1;
  border-color: #f1dfb5;
}

.content-upload-file__name {
  font-size: 14px;
  font-weight: 700;
  color: var(--admin-ink);
  word-break: break-all;
}

.content-upload-file__meta {
  margin-top: 4px;
  font-size: 12px;
  color: #68808e;
}

.header-actions,
.admin-filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.full-width {
  width: 100%;
}

@media (max-width: 960px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }

  .admin-hero,
  .workspace-card__header,
  .workspace-card__header--stack,
  .subsection-head,
  .quick-create-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .admin-stat-grid,
  .focus-grid {
    grid-template-columns: 1fr;
  }

  .admin-filter-select {
    width: 100%;
  }

  .chapter-header,
  .paper-title-row,
  .exam-toolbar,
  .section-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .chapter-progress {
    min-width: 0;
    width: 100%;
  }
}
</style>
