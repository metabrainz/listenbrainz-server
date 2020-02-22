import React from 'react'
import { mount } from 'enzyme'

import LastFmImporter from '../jsx/lastFmImporter'

let props;

describe('LastFmImporter is working correctly', () => {
  it('renders without crashing', () => {
    const wrapper = mount(<LastFmImporter {...props} />);
    expect(wrapper).toBeTruthy();
  })
});