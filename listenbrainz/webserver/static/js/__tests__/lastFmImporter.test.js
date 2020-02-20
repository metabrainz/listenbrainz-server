import React from 'react'
import ReactDOM from 'react-dom'
import { shallow } from 'enzyme'

import LastFmImporter from '../jsx/lastFmImporter'

let element;
let props;

describe('LastFmImporter is working correctly', () => {
  it('renders without crashing', () => {
    const div = document.createElement('div');
    ReactDOM.render(<LastFmImporter {...props}/>, div);
    ReactDOM.unmountComponentAtNode(div);
  })
  

});