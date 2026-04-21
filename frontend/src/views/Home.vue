<template>
  <div class="home-container">
    <div class="header">
      <h1 class="title">智能旅行规划助手</h1>
      <p class="subtitle">AI 驱动的一键式旅行行程设计</p>
    </div>

    <a-card class="form-card" :bordered="false">
      <a-form
        :model="formState"
        layout="vertical"
        @finish="onFinish"
      >
        <a-row :gutter="24">
          <!-- 目的地 -->
          <a-col :span="24">
            <a-form-item
              label="你想去哪个城市？"
              name="city"
              :rules="[{ required: true, message: '请输入目的地城市' }]"
            >
              <a-input
                v-model:value="formState.city"
                placeholder="例如：北京、西安、成都..."
                size="large"
              >
                <template #prefix>
                  <environment-outlined />
                </template>
              </a-input>
            </a-form-item>
          </a-col>

          <!-- 日期范围 -->
          <a-col :span="12">
            <a-form-item
              label="出发日期"
              name="start_date"
              :rules="[{ required: true, message: '请选择出发日期' }]"
            >
              <a-date-picker
                v-model:value="formState.start_date"
                placeholder="开始日期"
                size="large"
                style="width: 100%"
                :disabled-date="disabledDate"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item
              label="结束日期"
              name="end_date"
              :rules="[{ required: true, message: '请选择结束日期' }]"
            >
              <a-date-picker
                v-model:value="formState.end_date"
                placeholder="结束日期"
                size="large"
                style="width: 100%"
                :disabled-date="disabledDate"
              />
            </a-form-item>
          </a-col>

          <!-- 交通与住宿 -->
          <a-col :span="12">
            <a-form-item label="交通偏好" name="transportation">
              <a-select v-model:value="formState.transportation" size="large">
                <a-select-option value="公共交通">公共交通 (地铁/公交)</a-select-option>
                <a-select-option value="打车/自驾">打车/自驾</a-select-option>
                <a-select-option value="步行为主">步行为主</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="住宿要求" name="accommodation">
              <a-select v-model:value="formState.accommodation" size="large">
                <a-select-option value="经济型酒店">经济型酒店</a-select-option>
                <a-select-option value="舒适型酒店">舒适型酒店</a-select-option>
                <a-select-option value="高档豪华酒店">高档豪华酒店</a-select-option>
                <a-select-option value="民宿/客栈">民宿/客栈</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>

          <!-- 旅行偏好 -->
          <a-col :span="24">
            <a-form-item label="旅行偏好 (多选)" name="preferences">
              <a-checkbox-group v-model:value="formState.preferences">
                <a-checkbox value="历史文化">历史文化</a-checkbox>
                <a-checkbox value="自然风光">自然风光</a-checkbox>
                <a-checkbox value="当地美食">当地美食</a-checkbox>
                <a-checkbox value="亲子休闲">亲子休闲</a-checkbox>
                <a-checkbox value="潮流打卡">潮流打卡</a-checkbox>
                <a-checkbox value="购物狂欢">购物狂欢</a-checkbox>
              </a-checkbox-group>
            </a-form-item>
          </a-col>

          <!-- 自由输入 -->
          <a-col :span="24">
            <a-form-item label="还有什么特别要求吗？" name="free_text_input">
              <a-textarea
                v-model:value="formState.free_text_input"
                placeholder="比如：带着老人孩子，节奏慢一点；或者：想吃正宗的当地早餐..."
                :rows="4"
              />
            </a-form-item>
          </a-col>

          <!-- 提交按钮 -->
          <a-col :span="24" style="text-align: center; margin-top: 24px">
            <a-button
              type="primary"
              html-type="submit"
              size="large"
              :loading="loading"
              class="submit-btn"
            >
              立即生成旅行计划
            </a-button>
          </a-col>
        </a-row>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { EnvironmentOutlined } from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';
import dayjs, { Dayjs } from 'dayjs';
import { tripApi } from '../services/api';
import type { TripRequest } from '../types';

const router = useRouter();
const loading = ref(false);

const formState = reactive({
  city: '',
  start_date: null as Dayjs | null,
  end_date: null as Dayjs | null,
  transportation: '公共交通',
  accommodation: '经济型酒店',
  preferences: ['历史文化', '当地美食'],
  free_text_input: '',
});

// 禁止选择过去日期
const disabledDate = (current: Dayjs) => {
  return current && current < dayjs().startOf('day');
};

const onFinish = async () => {
  if (!formState.start_date || !formState.end_date) return;
  
  const days = formState.end_date.diff(formState.start_date, 'day') + 1;
  if (days <= 0) {
    message.error('结束日期必须晚于开始日期');
    return;
  }

  loading.value = true;
  try {
    const request: TripRequest = {
      ...formState,
      start_date: formState.start_date.format('YYYY-MM-DD'),
      end_date: formState.end_date.format('YYYY-MM-DD'),
      travel_days: days,
    };
    
    const plan = await tripApi.createPlan(request);
    
    // 跳转到结果页，并通过 state 传递数据
    router.push({
      name: 'Result',
      state: { plan: JSON.stringify(plan) }
    });
    
  } catch (error: any) {
    console.error('生成失败:', error);
    message.error('生成计划失败，请稍后再试');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.home-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 60px 20px;
}

.header {
  text-align: center;
  margin-bottom: 48px;
}

.title {
  font-size: 36px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 12px;
}

.subtitle {
  font-size: 18px;
  color: #666;
}

.form-card {
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  padding: 24px;
}

.submit-btn {
  height: 50px;
  padding: 0 48px;
  font-size: 18px;
  border-radius: 25px;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  border: none;
}

.submit-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.3);
}
</style>
