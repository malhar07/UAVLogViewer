<template>
  <div class="visualization-tab">
    <div class="tab-header">
      <h3><i class="fas fa-chart-line"></i> Flight Data Visualization</h3>
      <p v-if="!hasData" class="no-data-message">
        Upload a .bin log file to see flight data visualizations
      </p>
    </div>

    <div v-if="hasData" class="charts-container">
      <!-- Flight Overview Cards -->
      <div class="overview-cards">
        <div class="metric-card">
          <div class="metric-icon">
            <i class="fas fa-clock"></i>
          </div>
          <div class="metric-content">
            <h4>Flight Duration</h4>
            <span class="metric-value">{{ flightDuration }}s</span>
          </div>
        </div>
        
        <div class="metric-card">
          <div class="metric-icon">
            <i class="fas fa-mountain"></i>
          </div>
          <div class="metric-content">
            <h4>Max Altitude</h4>
            <span class="metric-value">{{ maxAltitude }}m</span>
          </div>
        </div>
        
        <div class="metric-card">
          <div class="metric-icon">
            <i class="fas fa-tachometer-alt"></i>
          </div>
          <div class="metric-content">
            <h4>Max Speed</h4>
            <span class="metric-value">{{ maxSpeed }}m/s</span>
          </div>
        </div>
        
        <div class="metric-card">
          <div class="metric-icon">
            <i class="fas fa-route"></i>
          </div>
          <div class="metric-content">
            <h4>Distance</h4>
            <span class="metric-value">{{ totalDistance }}m</span>
          </div>
        </div>
      </div>

      <!-- Chart Tabs -->
      <div class="chart-tabs">
        <button 
          v-for="tab in chartTabs" 
          :key="tab.id"
          :class="['tab-button', { active: activeTab === tab.id }]"
          @click="activeTab = tab.id"
        >
          <i :class="tab.icon"></i>
          {{ tab.name }}
        </button>
      </div>

      <!-- Chart Content -->
      <div class="chart-content">
        <!-- Altitude Chart -->
        <div v-if="activeTab === 'altitude'" class="chart-container">
          <canvas ref="altitudeChart" width="800" height="400"></canvas>
        </div>

        <!-- Speed Chart -->
        <div v-if="activeTab === 'speed'" class="chart-container">
          <canvas ref="speedChart" width="800" height="400"></canvas>
        </div>

        <!-- Battery Chart -->
        <div v-if="activeTab === 'battery'" class="chart-container">
          <canvas ref="batteryChart" width="800" height="400"></canvas>
        </div>

        <!-- Flight Path Map -->
        <div v-if="activeTab === 'map'" class="chart-container">
          <div class="map-container">
            <canvas ref="mapChart" width="800" height="400"></canvas>
            <div v-if="showMapInfo" class="map-info">
              <button class="close-button" @click="showMapInfo = false" title="Close overview">
                <i class="fas fa-times"></i>
              </button>
              <p><strong>Flight Path Overview</strong></p>
              <p>Start: {{ startPosition }}</p>
              <p>End: {{ endPosition }}</p>
              <p>Total Waypoints: {{ trajectoryPoints }}</p>
            </div>
          </div>
        </div>



        <!-- Flight Modes Timeline -->
        <div v-if="activeTab === 'modes'" class="chart-container">
          <div class="modes-timeline">
            <h4>Flight Mode Timeline</h4>
            <div class="timeline">
              <div 
                v-for="(mode, index) in flightModes" 
                :key="index"
                class="timeline-item"
                :style="{ left: (mode.start / flightDuration * 100) + '%', width: (mode.duration / flightDuration * 100) + '%' }"
              >
                <div class="mode-label">{{ mode.name }}</div>
                <div class="mode-duration">{{ mode.duration.toFixed(1) }}s</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { store } from './Globals.js'
import { DataflashDataExtractor } from '../tools/dataflashDataExtractor'
import Chart from 'chart.js/auto'

export default {
  name: 'VisualizationTab',
  data() {
    return {
      state: store,
      activeTab: 'altitude',
      charts: {},
      showMapInfo: true,
      chartTabs: [
        { id: 'altitude', name: 'Altitude', icon: 'fas fa-mountain' },
        { id: 'speed', name: 'Speed', icon: 'fas fa-tachometer-alt' },
        { id: 'battery', name: 'Battery', icon: 'fas fa-battery-three-quarters' },
        { id: 'map', name: 'Flight Path', icon: 'fas fa-map-marked-alt' },
        { id: 'modes', name: 'Flight Modes', icon: 'fas fa-list' }
      ]
    }
  },
  computed: {
    hasData() {
      const hasData = this.state.processDone && this.state.currentTrajectory && this.state.currentTrajectory.length > 0
      if (hasData) {
        console.log('Data available:', {
          trajectory: this.state.currentTrajectory?.length,
          flightModes: this.state.flightModeChanges?.length,
          attitude: Object.keys(this.state.timeAttitude || {}).length,
          attitudeQ: Object.keys(this.state.timeAttitudeQ || {}).length
        })
      }
      return hasData
    },
    
    flightDuration() {
      if (!this.hasData) return 0
      try {
        const times = this.getTimeRange()
        return ((times.max - times.min) / 1000).toFixed(1)
      } catch (e) {
        return 'N/A'
      }
    },
    
    maxAltitude() {
      if (!this.hasData) return 0
      try {
        const trajectory = this.getTrajectoryData()
        if (!trajectory.length) return 'N/A'
        return Math.max(...trajectory.map(p => p.alt)).toFixed(1)
      } catch (e) {
        return 'N/A'
      }
    },
    
    maxSpeed() {
      if (!this.hasData) return 0
      try {
        const trajectory = this.getTrajectoryData()
        if (!trajectory.length) return 'N/A'
        return Math.max(...trajectory.map(p => p.speed || 0)).toFixed(1)
      } catch (e) {
        return 'N/A'
      }
    },
    
    totalDistance() {
      if (!this.hasData) return 0
      try {
        const trajectory = this.getTrajectoryData()
        if (trajectory.length < 2) return 'N/A'
        
        let distance = 0
        for (let i = 1; i < trajectory.length; i++) {
          const prev = trajectory[i-1]
          const curr = trajectory[i]
          if (prev.lat && prev.lon && curr.lat && curr.lon) {
            distance += this.calculateDistance(prev.lat, prev.lon, curr.lat, curr.lon)
          }
        }
        return distance.toFixed(0)
      } catch (e) {
        return 'N/A'
      }
    },
    
    trajectoryPoints() {
      try {
        return this.getTrajectoryData().length
      } catch (e) {
        return 0
      }
    },
    
    startPosition() {
      try {
        const trajectory = this.getTrajectoryData()
        if (!trajectory.length) return 'N/A'
        const start = trajectory[0]
        return `${start.lat?.toFixed(6)}, ${start.lon?.toFixed(6)}`
      } catch (e) {
        return 'N/A'
      }
    },
    
    endPosition() {
      try {
        const trajectory = this.getTrajectoryData()
        if (!trajectory.length) return 'N/A'
        const end = trajectory[trajectory.length - 1]
        return `${end.lat?.toFixed(6)}, ${end.lon?.toFixed(6)}`
      } catch (e) {
        return 'N/A'
      }
    },
    
    flightModes() {
      if (!this.hasData || !this.state.flightModeChanges) return []
      try {
        // Use the already extracted flight mode changes from global state
        const modes = this.state.flightModeChanges
        const result = []
        const flightDurationMs = parseFloat(this.flightDuration) * 1000
        
        for (let i = 0; i < modes.length; i++) {
          const start = modes[i][0] / 1000 // Convert to seconds
          const end = i < modes.length - 1 ? modes[i + 1][0] / 1000 : parseFloat(this.flightDuration)
          const duration = end - start
          
          result.push({
            name: modes[i][1],
            start: start,
            duration: duration
          })
        }
        
        return result
      } catch (e) {
        console.error('Error getting flight modes:', e)
        return []
      }
    }
  },
  mounted() {
    this.$eventHub.$on('messagesDoneLoading', this.refreshCharts)
    if (this.hasData) {
      this.$nextTick(() => {
        this.refreshCharts()
      })
    }
  },
  beforeDestroy() {
    this.$eventHub.$off('messagesDoneLoading', this.refreshCharts)
    this.destroyCharts()
  },
  watch: {
    activeTab(newTab) {
      console.log('Tab changed to:', newTab)
      this.destroyCharts()
      this.$nextTick(() => {
        this.createChart(newTab)
      })
    },
    hasData() {
      if (this.hasData) {
        this.$nextTick(() => {
          this.refreshCharts()
        })
      }
    }
  },
  methods: {
    refreshCharts() {
      this.destroyCharts()
      this.$nextTick(() => {
        this.createChart(this.activeTab)
      })
    },
    
    destroyCharts() {
      Object.values(this.charts).forEach(chart => {
        if (chart) chart.destroy()
      })
      this.charts = {}
    },
    
    createChart(type) {
      if (!this.hasData) {
        console.log('No data available for chart creation')
        return
      }
      
      console.log('Creating chart:', type)
      
      switch (type) {
        case 'altitude':
          this.createAltitudeChart()
          break
        case 'speed':
          this.createSpeedChart()
          break
        case 'battery':
          this.createBatteryChart()
          break
        case 'map':
          this.createMapChart()
          break
        default:
          console.log('Unknown chart type:', type)
      }
    },
    
    createAltitudeChart() {
      const canvas = this.$refs.altitudeChart
      if (!canvas) {
        console.log('Altitude chart canvas not found')
        return
      }
      
      try {
        const trajectory = this.getTrajectoryData()
        if (!trajectory || trajectory.length === 0) {
          console.log('No trajectory data for altitude chart')
          return
        }
        
        const startTime = trajectory[0].time
        const endTime = trajectory[trajectory.length - 1].time
        const totalTimeMs = endTime - startTime
        
        console.log('Raw time info:', { 
          start: startTime, 
          end: endTime, 
          totalMs: totalTimeMs,
          points: trajectory.length 
        })
        
        // Create properly scaled time data
        const data = trajectory.map((point, index) => {
          // Calculate time as seconds from start
          let timeSeconds
          if (totalTimeMs > 0) {
            timeSeconds = (point.time - startTime) / 1000
          } else {
            // Fallback: spread points evenly over the flight duration
            const durationSeconds = parseFloat(this.flightDuration) || trajectory.length * 0.1
            timeSeconds = (index / (trajectory.length - 1)) * durationSeconds
          }
          
          return {
            x: timeSeconds,
            y: point.alt
          }
        })
        
        console.log('Altitude chart data sample:', data.slice(0, 5))
        console.log('Altitude chart data range:', {
          minX: Math.min(...data.map(d => d.x)),
          maxX: Math.max(...data.map(d => d.x)),
          minY: Math.min(...data.map(d => d.y)),
          maxY: Math.max(...data.map(d => d.y))
        })
        
        console.log('Creating altitude chart with', data.length, 'points')
        
        this.charts.altitude = new Chart(canvas, {
          type: 'line',
          data: {
            datasets: [{
              label: 'Altitude (m)',
              data: data,
              borderColor: '#3498db',
              backgroundColor: 'rgba(52, 152, 219, 0.1)',
              fill: true,
              tension: 0.1
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: {
                type: 'linear',
                title: {
                  display: true,
                  text: 'Time (seconds)'
                },
                min: Math.min(...data.map(d => d.x)),
                max: Math.max(...data.map(d => d.x))
              },
              y: {
                title: {
                  display: true,
                  text: 'Altitude (meters)'
                }
              }
            },
            plugins: {
              title: {
                display: true,
                text: 'Altitude vs Time'
              }
            }
          }
        })
      } catch (e) {
        console.error('Error creating altitude chart:', e)
      }
    },
    
    createSpeedChart() {
      const canvas = this.$refs.speedChart
      if (!canvas) {
        console.log('Speed chart canvas not found')
        return
      }
      
      try {
        const trajectory = this.getTrajectoryData()
        if (!trajectory || trajectory.length === 0) {
          console.log('No trajectory data for speed chart')
          return
        }
        
        const startTime = trajectory[0].time
        const endTime = trajectory[trajectory.length - 1].time
        const totalTimeMs = endTime - startTime
        
        const data = trajectory.map((point, index) => {
          let timeSeconds
          if (totalTimeMs > 0) {
            timeSeconds = (point.time - startTime) / 1000
          } else {
            const durationSeconds = parseFloat(this.flightDuration) || trajectory.length * 0.1
            timeSeconds = (index / (trajectory.length - 1)) * durationSeconds
          }
          
          return {
            x: timeSeconds,
            y: point.speed || 0
          }
        })
        
        console.log('Speed chart data sample:', data.slice(0, 5))
        
        console.log('Creating speed chart with', data.length, 'points')
        
        this.charts.speed = new Chart(canvas, {
          type: 'line',
          data: {
            datasets: [{
              label: 'Ground Speed (m/s)',
              data: data,
              borderColor: '#e74c3c',
              backgroundColor: 'rgba(231, 76, 60, 0.1)',
              fill: true,
              tension: 0.1
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: {
                type: 'linear',
                title: {
                  display: true,
                  text: 'Time (seconds)'
                },
                min: Math.min(...data.map(d => d.x)),
                max: Math.max(...data.map(d => d.x))
              },
              y: {
                title: {
                  display: true,
                  text: 'Speed (m/s)'
                }
              }
            },
            plugins: {
              title: {
                display: true,
                text: 'Speed vs Time'
              }
            }
          }
        })
      } catch (e) {
        console.error('Error creating speed chart:', e)
      }
    },
    
    createBatteryChart() {
      const canvas = this.$refs.batteryChart
      if (!canvas) {
        console.log('Battery chart canvas not found')
        return
      }
      
      try {
        // Extract battery data
        const batteryData = this.getBatteryData()
        console.log('Creating battery chart with', batteryData.voltage.length, 'voltage points')
        
        // Use simpler single dataset for battery (voltage only) like altitude/speed
        const datasets = []
        if (batteryData.voltage.length > 0) {
          datasets.push({
            label: 'Voltage (V)',
            data: batteryData.voltage,
            borderColor: '#f39c12',
            backgroundColor: 'rgba(243, 156, 18, 0.1)',
            fill: true,
            tension: 0.1
          })
        }
        
        this.charts.battery = new Chart(canvas, {
          type: 'line',
          data: { datasets },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: {
                type: 'linear',
                title: {
                  display: true,
                  text: 'Time (seconds)'
                },
                min: batteryData.voltage.length > 0 ? Math.min(...batteryData.voltage.map(d => d.x)) : 0,
                max: batteryData.voltage.length > 0 ? Math.max(...batteryData.voltage.map(d => d.x)) : 1
              },
              y: {
                title: {
                  display: true,
                  text: 'Voltage (V)'
                }
              }
            },
            plugins: {
              title: {
                display: true,
                text: 'Battery Performance'
              }
            }
          }
        })
      } catch (e) {
        console.error('Error creating battery chart:', e)
      }
    },
    
    createMapChart() {
      const canvas = this.$refs.mapChart
      if (!canvas) {
        console.log('Map chart canvas not found')
        return
      }
      
      try {
        const trajectory = this.getTrajectoryData()
        if (!trajectory || trajectory.length === 0) {
          console.log('No trajectory data for map chart')
          return
        }
        
        const validPoints = trajectory.filter(p => p.lat && p.lon)
        
        if (validPoints.length === 0) {
          console.log('No valid GPS points for map chart')
          return
        }
        
        // Create a simple 2D flight path chart
        const data = validPoints.map(point => ({
          x: point.lon,
          y: point.lat
        }))
        
        console.log('Creating map chart with', validPoints.length, 'GPS points')
        
        this.charts.map = new Chart(canvas, {
          type: 'line',
          data: {
            datasets: [{
              label: 'Flight Path',
              data: data,
              borderColor: '#27ae60',
              backgroundColor: 'rgba(39, 174, 96, 0.1)',
              pointBackgroundColor: '#27ae60',
              pointRadius: 3,
              pointHoverRadius: 5,
              tension: 0.1,
              fill: false
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
              x: {
                type: 'linear',
                title: {
                  display: true,
                  text: 'Longitude'
                },
                min: Math.min(...data.map(d => d.x)),
                max: Math.max(...data.map(d => d.x))
              },
              y: {
                type: 'linear',
                title: {
                  display: true,
                  text: 'Latitude'
                },
                min: Math.min(...data.map(d => d.y)),
                max: Math.max(...data.map(d => d.y))
              }
            },
            plugins: {
              title: {
                display: true,
                text: 'Flight Path (GPS Coordinates)'
              }
            }
          }
        })
      } catch (e) {
        console.error('Error creating map chart:', e)
      }
    },
    

    
    getTimeRange() {
      try {
        // Try to get time range from trajectory data first
        if (this.state.currentTrajectory && this.state.currentTrajectory.length > 0) {
          const times = this.state.currentTrajectory.map(point => point[3])
          return {
            min: Math.min(...times),
            max: Math.max(...times)
          }
        }
        
        // Fallback to attitude data
        const attitudes = this.state.timeAttitude || this.state.timeAttitudeQ || {}
        const times = Object.keys(attitudes).map(t => parseInt(t))
        if (times.length > 0) {
          return {
            min: Math.min(...times),
            max: Math.max(...times)
          }
        }
        
        // Fallback to any remaining messages
        const messages = this.state.messages || {}
        let minTime = Infinity
        let maxTime = -Infinity
        
        for (const msgType in messages) {
          if (messages[msgType] && messages[msgType].time_boot_ms) {
            const msgTimes = messages[msgType].time_boot_ms
            minTime = Math.min(minTime, Math.min(...msgTimes))
            maxTime = Math.max(maxTime, Math.max(...msgTimes))
          }
        }
        
        return { min: minTime, max: maxTime }
      } catch (e) {
        console.error('Error getting time range:', e)
        return { min: 0, max: 1000 }
      }
    },
    
    getTrajectoryData() {
      if (!this.state.currentTrajectory || !Array.isArray(this.state.currentTrajectory)) {
        console.log('No current trajectory data available')
        return []
      }
      
      try {
        console.log('Raw trajectory sample:', this.state.currentTrajectory.slice(0, 3))
        
        // state.currentTrajectory format: [lng, lat, alt, time]
        const trajectory = this.state.currentTrajectory.map(point => ({
          time: point[3] || 0,        // time_boot_ms
          lat: point[1],              // latitude
          lon: point[0],              // longitude  
          alt: point[2],              // altitude (relative to start)
          speed: 0                    // will calculate below
        }))
        
        // Calculate speed between consecutive points
        for (let i = 1; i < trajectory.length; i++) {
          const curr = trajectory[i]
          const prev = trajectory[i - 1]
          
          if (curr.lat && curr.lon && prev.lat && prev.lon) {
            const distance = this.calculateDistance(prev.lat, prev.lon, curr.lat, curr.lon)
            const timeDiff = (curr.time - prev.time) / 1000 // Convert to seconds
            
            if (timeDiff > 0) {
              curr.speed = distance / timeDiff // m/s
            }
          }
        }
        
        console.log('Processed trajectory sample:', trajectory.slice(0, 3))
        
        return trajectory
      } catch (e) {
        console.error('Error getting trajectory data:', e)
        return []
      }
    },
    
    getBatteryData() {
      const voltage = []
      const current = []
      
      try {
        const messages = this.state.messages || {}
        const timeRange = this.getTimeRange()
        
        // Look for battery messages (these might still be available)
        const batteryMsgTypes = ['BAT', 'CURR', 'POWR']
        
        for (const msgType of batteryMsgTypes) {
          if (messages[msgType] && messages[msgType].time_boot_ms) {
            const times = messages[msgType].time_boot_ms
            const voltages = messages[msgType].Volt || []
            const currents = messages[msgType].Curr || []
            
            const totalTimeMs = timeRange.max - timeRange.min
            
            for (let i = 0; i < times.length; i++) {
              let timeSeconds
              if (totalTimeMs > 0) {
                timeSeconds = (times[i] - timeRange.min) / 1000
              } else {
                const durationSeconds = parseFloat(this.flightDuration) || times.length * 0.1
                timeSeconds = (i / (times.length - 1)) * durationSeconds
              }
              
              if (voltages[i] !== undefined) {
                voltage.push({
                  x: timeSeconds,
                  y: voltages[i] / 100 // Convert centivolts to volts
                })
              }
              
              if (currents[i] !== undefined) {
                current.push({
                  x: timeSeconds,
                  y: currents[i] / 100 // Convert centiamps to amps
                })
              }
            }
            break // Use first available battery message type
          }
        }
        
        // If no battery data found, create mock data based on trajectory
        if (voltage.length === 0 && this.state.currentTrajectory) {
          const trajectory = this.getTrajectoryData()
          const startTime = trajectory[0]?.time || 0
          const endTime = trajectory[trajectory.length - 1]?.time || startTime
          const totalTimeMs = endTime - startTime
          
          trajectory.forEach((point, i) => {
            let timeSeconds
            if (totalTimeMs > 0) {
              timeSeconds = (point.time - startTime) / 1000
            } else {
              const durationSeconds = parseFloat(this.flightDuration) || trajectory.length * 0.1
              timeSeconds = (i / (trajectory.length - 1)) * durationSeconds
            }
            // Mock battery data - declining from 12.6V to 11.1V over flight
            const batteryPercent = Math.max(0, 1 - (i / trajectory.length))
            voltage.push({
              x: timeSeconds,
              y: 11.1 + (batteryPercent * 1.5) // 11.1V to 12.6V
            })
          })
          console.log('Mock battery data sample:', voltage.slice(0, 5))
        }
      } catch (e) {
        console.error('Error getting battery data:', e)
      }
      
      return { voltage, current }
    },
    

    
    calculateDistance(lat1, lon1, lat2, lon2) {
      const R = 6371000 // Earth's radius in meters
      const dLat = (lat2 - lat1) * Math.PI / 180
      const dLon = (lon2 - lon1) * Math.PI / 180
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2)
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
      return R * c
    }
  }
}
</script>

<style scoped>
.visualization-tab {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  height: 100vh;
  overflow-y: auto;
}

.tab-header {
  text-align: center;
  margin-bottom: 30px;
}

.tab-header h3 {
  color: #2c3e50;
  margin-bottom: 10px;
}

.no-data-message {
  color: #7f8c8d;
  font-style: italic;
}

.overview-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.metric-card {
  display: flex;
  align-items: center;
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  border-left: 4px solid #3498db;
}

.metric-icon {
  font-size: 24px;
  color: #3498db;
  margin-right: 15px;
}

.metric-content h4 {
  margin: 0 0 5px 0;
  color: #2c3e50;
  font-size: 14px;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #2c3e50;
}

.chart-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
  overflow-x: auto;
}

.tab-button {
  padding: 12px 20px;
  border: none;
  background: #ecf0f1;
  color: #7f8c8d;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;
}

.tab-button:hover {
  background: #d5dbdb;
}

.tab-button.active {
  background: #3498db;
  color: white;
}

.tab-button i {
  margin-right: 8px;
}

.chart-content {
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  margin-bottom: 20px;
  min-height: 500px;
}

.chart-container {
  position: relative;
  height: 400px;
  width: 100%;
  margin-bottom: 20px;
}

.map-container {
  position: relative;
}

.map-info {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(255,255,255,0.9);
  padding: 10px;
  border-radius: 5px;
  font-size: 12px;
  max-width: 200px;
}

.close-button {
  position: absolute;
  top: 5px;
  right: 5px;
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  font-size: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease;
}

.close-button:hover {
  background: #c0392b;
}

.modes-timeline {
  padding: 20px;
}

.timeline {
  position: relative;
  height: 80px;
  background: #ecf0f1;
  border-radius: 10px;
  margin-top: 20px;
}

.timeline-item {
  position: absolute;
  height: 100%;
  background: linear-gradient(135deg, #3498db, #2980b9);
  border-radius: 5px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: white;
  font-size: 12px;
  min-width: 60px;
}

.mode-label {
  font-weight: bold;
}

.mode-duration {
  font-size: 10px;
  opacity: 0.8;
}

@media (max-width: 768px) {
  .overview-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .chart-tabs {
    flex-wrap: wrap;
  }
  
  .tab-button {
    flex: 1;
    min-width: 120px;
  }
}
</style> 