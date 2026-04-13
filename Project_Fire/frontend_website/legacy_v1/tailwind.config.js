/** @type {import('tailwindcss').Config} */
module.exports = {
    content: ["./index.html", "./js/**/*.js"],
    darkMode: "class",
    theme: {
        extend: {
            colors: {
                primary: "#FF4B4B",
                warning: "#FFB347",
                "danger-deep": "#D93636",
                "surface-light": "#F9FAFB",
                "background-light": "#ffffff",
                "text-main": "#0F172A",
                "text-muted": "#64748B",
            },
            fontFamily: {
                display: ["Manrope", "sans-serif"],
                mono: ["JetBrains Mono", "monospace"],
            },
            borderRadius: {
                DEFAULT: "0.25rem",
                lg: "0.5rem",
                xl: "0.75rem",
                "2xl": "1rem",
                "3xl": "1.5rem",
                full: "9999px",
            },
            keyframes: {
                fadeIn: {
                    "0%": { opacity: "0" },
                    "100%": { opacity: "1" },
                },
                scaleUp: {
                    "0%": { transform: "scale(0.95)", opacity: "0" },
                    "100%": { transform: "scale(1)", opacity: "1" },
                },
                slideIn: {
                    "0%": { transform: "translateX(100%)", opacity: "0" },
                    "100%": { transform: "translateX(0)", opacity: "1" },
                },
            },
            animation: {
                "fade-in": "fadeIn 0.3s ease-out forwards",
                "scale-up": "scaleUp 0.3s ease-out forwards",
                "slide-in": "slideIn 0.3s ease-out forwards",
            },
        },
    },
    plugins: [
        require("@tailwindcss/forms"),
        require("@tailwindcss/container-queries"),
    ],
};
