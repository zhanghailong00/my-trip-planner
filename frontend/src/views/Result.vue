<template>
  <div class="result-container">
    <!-- 顶部摘要 -->
    <div class="summary-header">
      <a-button type="link" @click="router.push('/')" class="back-btn">
        <template #icon><left-outlined /></template>
        重新规划
      </a-button>
      <h1 class="city-title">{{ plan?.city }} {{ plan?.days }}日游计划</h1>
      <div class="date-info">
        <calendar-outlined /> {{ plan?.start_date }} 至 {{ plan?.end_date }}
      </div>
    </div>

    <div class="content-layout">
      <!-- 左侧行程列表 -->
      <div class="itinerary-side">
        <a-tabs v-model:activeKey="activeDay">
          <a-tab-pane v-for="(day, index) in plan?.days_plan" :key="index" :tab="'第' + (index + 1) + '天'">
            <div class="day-content">
              <div class="weather-card" v-if="day.weather">
                <span class="weather-text">
                  <cloud-outlined /> {{ day.weather.day_weather }} / {{ day.weather.night_weather }} 
                  <span class="temp">{{ day.weather.day_temp }}°C ~ {{ day.weather.night_temp }}°C</span>
                </span>
              </div>

              <a-timeline>
                <!-- 景点 -->
                <a-timeline-item v-for="attraction in day.attractions" :key="attraction.name" color="blue">
                  <template #dot><environment-filled /></template>
                  <div class="item-card clickable" @click="focusMarker(attraction)">
                    <h3 class="item-name">{{ attraction.name }}</h3>
                    <p class="item-desc">{{ attraction.description }}</p>
                    <div class="item-meta">
                      <span><clock-circle-outlined /> 建议游览 {{ attraction.visit_duration }} 分钟</span>
                      <span v-if="attraction.ticket_price > 0"> 🎫 ￥{{ attraction.ticket_price }}</span>
                    </div>
                  </div>
                </a-timeline-item>

                <!-- 餐饮 -->
                <a-timeline-item v-for="meal in day.meals" :key="meal.name" color="orange">
                  <template #dot><coffee-outlined /></template>
                  <div class="item-card">
                    <h3 class="item-name">🍽️ {{ meal.name }} ({{ meal.type === 'lunch' ? '午餐' : meal.type === 'dinner' ? '晚餐' : '早餐' }})</h3>
                    <p class="item-desc">{{ meal.description }}</p>
                    <div class="item-meta">预估费用: ￥{{ meal.estimated_cost }}</div>
                  </div>
                </a-timeline-item>

                <!-- 酒店 -->
                <a-timeline-item v-if="day.hotel" color="purple">
                  <template #dot><home-filled /></template>
                  <div class="item-card">
                    <h3 class="item-name">🏨 住宿：{{ day.hotel.name }}</h3>
                    <p class="item-desc">{{ day.hotel.address }}</p>
                    <div class="item-meta">预估费用: ￥{{ day.hotel.estimated_cost }}/晚</div>
                  </div>
                </a-timeline-item>
              </a-timeline>
            </div>
          </a-tab-pane>
        </a-tabs>

        <!-- 预算与建议 -->
        <a-card title="预算明细" :bordered="false" class="info-card">
          <a-row :gutter="16">
            <a-col :span="6">
              <a-statistic title="景点" :value="plan?.budget.total_attractions" prefix="￥" />
            </a-col>
            <a-col :span="6">
              <a-statistic title="住宿" :value="plan?.budget.total_hotels" prefix="￥" />
            </a-col>
            <a-col :span="6">
              <a-statistic title="餐饮" :value="plan?.budget.total_meals" prefix="￥" />
            </a-col>
            <a-col :span="6">
              <a-statistic title="总计" :value="plan?.budget.total" prefix="￥" :value-style="{ color: '#3f8600' }" />
            </a-col>
          </a-row>
        </a-card>

        <a-card title="出行建议" :bordered="false" class="info-card suggestion-card">
          <p>{{ plan?.overall_suggestions }}</p>
        </a-card>
      </div>

      <!-- 右侧地图 -->
      <div class="map-side">
        <div id="map-container"></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { 
  LeftOutlined, EnvironmentFilled, CoffeeOutlined, HomeFilled, 
  ClockCircleOutlined, CalendarOutlined, CloudOutlined 
} from '@ant-design/icons-vue';
import AMapLoader from '@amap/amap-jsapi-loader';
import type { TripPlan, Attraction } from '../types';

const router = useRouter();
const plan = ref<TripPlan | null>(null);
const activeDay = ref(0);
let map: any = null;
let markers: any[] = [];

onMounted(() => {
  // 设置高德地图安全密钥 (从环境变量读取)
  (window as any)._AMapSecurityConfig = {
    securityJsCode: import.meta.env.VITE_AMAP_SECURITY_CODE,
  };
  
  // 从路由状态中获取数据
  const planJson = window.history.state.plan;
  if (planJson) {
    plan.value = JSON.parse(planJson);
    initMap();
  } else {
    router.push('/');
  }
});

const initMap = () => {
  AMapLoader.load({
    key: import.meta.env.VITE_AMAP_JS_KEY, // 从环境变量读取
    version: '2.0',
    plugins: ['AMap.Marker', 'AMap.InfoWindow'],
  }).then((AMap) => {
    map = new AMap.Map('map-container', {
      viewMode: '3D',
      zoom: 11,
      center: [108.940178, 34.2670], // 默认西安，会根据景点自动调整
    });

    // 渲染所有景点的标记
    renderMarkers(AMap);
  }).catch(e => {
    console.error('地图加载失败:', e);
  });
};

const renderMarkers = (AMap: any) => {
  if (!plan.value) return;
  
  // 清除旧标记
  markers.forEach(m => m.setMap(null));
  markers = [];

  const allAttractions = plan.value.days_plan.flatMap(d => d.attractions);
  const bounds = new AMap.Bounds();

  allAttractions.forEach(att => {
    const marker = new AMap.Marker({
      position: [att.location.longitude, att.location.latitude],
      title: att.name,
      map: map
    });

    const infoWindow = new AMap.InfoWindow({
      content: `<div style="padding: 10px;"><b>${att.name}</b><br/>${att.address}</div>`,
      offset: new AMap.Pixel(0, -30)
    });

    marker.on('click', () => {
      infoWindow.open(map, marker.getPosition());
    });

    markers.push(marker);
    bounds.extend(marker.getPosition());
  });

  // 自动缩放地图以适应所有标记
  if (allAttractions.length > 0) {
    map.setBounds(bounds);
  }
};

const focusMarker = (att: Attraction) => {
  if (map) {
    map.setZoomAndCenter(15, [att.location.longitude, att.location.latitude]);
  }
};

onUnmounted(() => {
  if (map) {
    map.destroy();
  }
});
</script>

<style scoped>
.result-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.summary-header {
  background: #fff;
  padding: 16px 40px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  z-index: 10;
}

.back-btn {
  padding-left: 0;
  margin-bottom: 8px;
}

.city-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.date-info {
  color: #666;
  font-size: 14px;
}

.content-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.itinerary-side {
  width: 500px;
  background: #fff;
  border-right: 1px solid #eee;
  padding: 0 24px 24px;
  overflow-y: auto;
}

.map-side {
  flex: 1;
  position: relative;
}

#map-container {
  width: 100%;
  height: 100%;
}

.day-content {
  padding-top: 16px;
}

.weather-card {
  background: #e6f7ff;
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 24px;
}

.temp {
  margin-left: 12px;
  font-weight: bold;
  color: #1890ff;
}

.item-card {
  background: #f9f9f9;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 8px;
  transition: all 0.3s;
}

.item-card.clickable:hover {
  cursor: pointer;
  background: #fff;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border-color: #1890ff;
}

.item-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.item-desc {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.item-meta {
  font-size: 12px;
  color: #999;
}

.info-card {
  margin-top: 24px;
  background: #fafafa;
}

.suggestion-card p {
  line-height: 1.8;
  color: #444;
}
</style>
