import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import Data from './Data';
import Panel from './artist-panel/Panel';
import SearchBox from './artist-search/SearchBox';
const root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);
root.render(
  <React.StrictMode>
    <div className="main-container">
      <Data />
    </div>
  </React.StrictMode>
);

