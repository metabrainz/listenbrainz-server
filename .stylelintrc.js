module.exports = {
  extends: "stylelint-config-recommended-scss",
  plugins: ["stylelint-prettier"],
  rules: {
    "prettier/prettier": true,
    "no-descending-specificity": null,
    "function-calc-no-unspaced-operator": null,
  },
}
