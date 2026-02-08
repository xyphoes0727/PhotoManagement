import React from 'react';
import { useLocation } from 'react-router-dom';
import { Bell, Settings, User } from 'lucide-react';
import './Header.css';

const Header = () => {
  const location = useLocation();

  const getPageTitle = () => {
    switch (location.pathname) {
      case '/':
        return 'Dashboard';
      case '/upload':
        return 'Upload Photos';
      case '/search':
        return 'Search Photos';
      case '/gallery':
        return 'Photo Gallery';
      case '/albums':
        return 'Albums';
      default:
        return 'Photo Management';
    }
  };

  return (
    <header className="header">
      <div className="header-left">
        <h1 className="page-title">{getPageTitle()}</h1>
      </div>

      <div className="header-right">
        <button className="header-btn">
          <Bell size={20} />
        </button>
        <button className="header-btn">
          <Settings size={20} />
        </button>
        <div className="user-menu">
          <div className="user-avatar">
            <User size={20} />
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
