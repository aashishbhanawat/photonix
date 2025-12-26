import { extendTheme } from '@chakra-ui/react'

const customTheme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
})

export default customTheme
