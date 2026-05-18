import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Upload, 
  Search, 
  Image, 
  Users,
  TrendingUp,
  FolderOpen
} from 'lucide-react';
import { getStats } from '../services/api';
import './Dashboard.css';

const Dashboard = () => {
  const [stats, setStats] = useState({ totalPhotos: 0, totalAlbums: 0, totalFaces: 0, photosThisMonth: 0 });
  const [loading, setLoading] = useState(true);
  const recentActivity = [];

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getStats();
        setStats({
          totalPhotos: data.totalPhotos || 0,
          totalAlbums: data.totalAlbums || 0,
          totalFaces: data.totalFaces || 0,
          thisMonth: data.photosThisMonth || 0
        });
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  const statCards = [
    { icon: Image, label: 'Total Photos', value: stats.totalPhotos.toString(), trend: stats.thisMonth > 0 ? `+${stats.thisMonth}` : '0' },
    { icon: FolderOpen, label: 'Albums', value: stats.totalAlbums.toString(), trend: '' },
    { icon: Users, label: 'Faces Detected', value: stats.totalFaces.toString(), trend: '' },
    { icon: TrendingUp, label: 'This Month', value: (stats.thisMonth || 0).toString(), trend: '' },
  ];

  const quickActions = [
    { icon: Upload, label: 'Upload Photos', path: '/upload', color: '#6366f1' },
    { icon: Search, label: 'Search Photos', path: '/search', color: '#8b5cf6' },
    { icon: Image, label: 'View Gallery', path: '/gallery', color: '#22c55e' },
    { icon: FolderOpen, label: 'Browse Albums', path: '/albums', color: '#f59e0b' },
  ];

  return (
    <div className="dashboard">
      <section className="stats-section">
        <div className="stats-grid">
          {statCards.map(({ icon: Icon, label, value, trend }) => (
            <div key={label} className="stat-card">
              <div className="stat-icon">
                <Icon size={24} />
              </div>
              <div className="stat-info">
                <span className="stat-value">{value}</span>
                <span className="stat-label">{label}</span>
              </div>
              {trend && <span className="stat-trend positive">{trend}</span>}
            </div>
          ))}
        </div>
      </section>

      <section className="quick-actions-section">
        <h2 className="section-title">Quick Actions</h2>
        <div className="quick-actions-grid">
          {quickActions.map(({ icon: Icon, label, path, color }) => (
            <Link key={path} to={path} className="quick-action-card">
              <div className="action-icon" style={{ backgroundColor: color }}>
                <Icon size={28} color="white" />
              </div>
              <span className="action-label">{label}</span>
            </Link>
          ))}
        </div>
      </section>

      <div className="dashboard-bottom">
        <section className="recent-section">
          <h2 className="section-title">Recent Activity</h2>
          <div className="activity-list">
            <div className="no-activity">
              <p>No recent activity. Start by uploading some photos!</p>
            </div>
          </div>
        </section>

        <section className="tips-section">
          <h2 className="section-title">AI Features</h2>
          <div className="tips-list">
            <div className="tip-card">
              <h3>🔍 Smart Search</h3>
              <p>Search your photos using natural language like "photos at the beach" or "birthday party"</p>
            </div>
            <div className="tip-card">
              <h3>🏷️ Auto Captioning</h3>
              <p>AI automatically generates descriptive captions for your uploaded photos</p>
            </div>
            <div className="tip-card">
              <h3>👤 Face Detection</h3>
              <p>Automatically detect and group photos by the people in them</p>
            </div>
            <div className="tip-card">
              <h3>📁 Smart Albums</h3>
              <p>AI suggests album categorizations based on photo content</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default Dashboard;
