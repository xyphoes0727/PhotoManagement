import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard';
import Upload from './pages/Upload';
import Search from './pages/Search';
import Gallery from './pages/Gallery';
import Albums from './pages/Albums';
import './App.css';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/search" element={<Search />} />
          <Route path="/gallery" element={<Gallery />} />
          <Route path="/albums" element={<Albums />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
