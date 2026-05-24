export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // Основные цвета из courier_full_screens_v2.html
        ink: {
          DEFAULT: '#1a1a1a',
          2: '#444',
          3: '#777',
        },
        bg: {
          DEFAULT: '#ffffff',
          2: '#f5f5f3',
          3: '#ebebea',
        },
        border: 'rgba(0,0,0,0.14)',
        blue: {
          DEFAULT: '#1450a3',
          bg: '#e8f0fc',
          text: '#0d3a7a',
        },
        green: {
          DEFAULT: '#1d7a3a',
          bg: '#e6f5eb',
          text: '#145229',
        },
        amber: {
          DEFAULT: '#a35a00',
          bg: '#fff3e0',
          text: '#7a4000',
        },
        red: {
          DEFAULT: '#c0392b',
          bg: '#fdecea',
          text: '#8b1a10',
        },
        teal: {
          DEFAULT: '#0d6e5a',
          bg: '#e4f6f1',
          text: '#094d3e',
        },
      },
      fontSize: {
        'xxs': '0.625rem', // 10px
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
      },
    },
  },
  plugins: [],
}