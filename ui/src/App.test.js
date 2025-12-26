import React from 'react';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ChakraProvider } from '@chakra-ui/react';
import { Provider } from 'react-redux';
import { createStore } from 'redux';
import { MockedProvider } from '@apollo/client/testing';
import reducers from './stores';
import App from './components/App';

// Mock cookies
jest.mock('js-cookie', () => ({
  get: jest.fn(),
}));

const store = createStore(reducers);

test('renders without crashing', () => {
  render(
    <MockedProvider>
      <Provider store={store}>
        <ChakraProvider>
          <MemoryRouter>
            <App />
          </MemoryRouter>
        </ChakraProvider>
      </Provider>
    </MockedProvider>
  );
});
