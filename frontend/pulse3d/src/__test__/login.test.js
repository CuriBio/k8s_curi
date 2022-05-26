import {
  render,
  screen,
  fireEvent,
  act,
  waitFor,
} from "@testing-library/react";
import Login from "../pages/login";
import "@testing-library/jest-dom";

describe("Login", () => {
  it("renders a login form with input fields", () => {
    render(<Login />);

    const custInputField = document.querySelector("#customer_id");
    const userInputField = document.querySelector("#username");
    const pwInputField = document.querySelector("#password");

    expect(custInputField).toBeInTheDocument();
    expect(userInputField).toBeInTheDocument();
    expect(pwInputField).toBeInTheDocument();
  });

  it.each`
    input1           | input2
    ${"Customer ID"} | ${"Username"}
    ${"Customer ID"} | ${"Password"}
    ${"Username"}    | ${"Password"}
  `(
    "renders correct error message if field is left empty",
    ({ input1, input2 }) => {
      render(<Login />);

      const inputField1 = screen.getByLabelText(input1);
      const inputField2 = screen.getByLabelText(input2);

      fireEvent.input(inputField1, {
        target: { value: "testInput1" },
      });
      fireEvent.input(inputField2, {
        target: { value: "testInput2" },
      });

      const submitButton = screen.getByText("Submit");
      fireEvent.click(submitButton);

      const errorMessage = screen.getByRole("errorMsg");
      waitFor(() => {
        expect(errorMessage).toHaveValue("testInput");
      });
    }
  );
});
