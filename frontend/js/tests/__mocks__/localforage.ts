const localforageMock = {
  createInstance: jest.fn(() => ({
    setItem: jest.fn(),
    getItem: jest.fn(),
    removeItem: jest.fn(),
    keys: jest.fn().mockResolvedValue([]),
  })),
};

export default localforageMock;
