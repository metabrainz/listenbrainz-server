import React from 'react'
import { shallow } from 'enzyme'

import LastFmImporterModal from './lastFmImporterModal'

let wrapper = null;
describe('LastFmImporterModal is working correctly', () => {
  beforeEach(() => {
    // Mount each time
    wrapper = shallow(<LastFmImporterModal />);
  });

  it('renders without crashing', () => {
    expect(wrapper).toBeTruthy();
  })
});
