import React from 'react'
import { mount } from 'enzyme'

import LastFmImporter from './lastFmImporter'

describe('LastFmImporter is working correctly', () => {
  it('renders without crashing', () => {
    const wrapper = mount(<LastFmImporter />);
    expect(wrapper).toBeTruthy();
  })
});