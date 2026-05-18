import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { 
  Home, 
  Upload, 
  Search, 
  Image, 
  FolderOpen,
  Camera
} from 'lucide-react';
import './Sidebar.css';

const Sidebar = () => {
  const location = useLocation();

  const menuItems = [
    { path: '/', icon: Home, label: 'Dashboard' },
    { path: '/upload', icon: Upload, label: 'Upload' },
    { path: '/search', icon: Search, label: 'Search' },
    { path: '/gallery', icon: Image, label: 'Gallery' },
    { path: '/albums', icon: FolderOpen, label: 'Albums' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <Camera className="logo-icon" size={32} />
        <span className="logo-text">PhotoAI</span>
      </div>
      
      <nav className="sidebar-nav">
        <ul className="nav-list">
          {menuItems.map(({ path, icon: Icon, label }) => (
            <li key={path} className="nav-item">
              <NavLink 
                to={path} 
                className={({ isActive }) => 
                  `nav-link ${isActive ? 'active' : ''}`
                }
              >
                <Icon size={20} />
                <span>{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="sidebar-footer">
        <div className="storage-info">
          <div className="storage-label">
            <span>Storage Used</span>
            <span>2.4 GB / 10 GB</span>
          </div>
          <div className="storage-bar">
            <div className="storage-progress" style={{ width: '24%' }}></div>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
