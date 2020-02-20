import React from 'react'
import ReactDOM from 'react-dom'

import LastFmImporter from '../jsx/lastFmImporter'

let props;

describe('LastFmImporter is working correctly', () => {
  it('renders without crashing', () => {
    const div = document.createElement('div');
    ReactDOM.render(<LastFmImporter {...props} />, div);
    expect(div.firstChild).toBeTruthy();
    ReactDOM.unmountComponentAtNode(div);
  })
});