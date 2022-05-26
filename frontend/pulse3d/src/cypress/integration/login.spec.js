describe("Login homepage", () => {
  beforeEach(() => {
    cy.visit("http://localhost:3000/login");
  });
  const getInputByLabel = (label) => {
    return cy
      .contains("label", label)
      .invoke("attr", "for")
      .then((id) => {
        cy.get("#" + id);
      });
  };
  it("displays login modal with correct input fields", () => {
    const inputLabels = [
      {
        label: "Customer ID",
        value: "test ID",
      },
      {
        label: "Username",
        value: "test username",
      },
      ,
      {
        label: "Password",
        value: "test password",
      },
    ];

    inputLabels.forEach(({ label, value }) => {
      getInputByLabel(label).type(value);
      getInputByLabel(label).should("have.value", value);
    });
  });

  it("displays submit button with hover effect", () => {
    const submitButton = cy.get("button");

    // should default to dark blue
    submitButton.should("have.css", "background-color", "rgb(0, 38, 62)");
    submitButton.contains("Submit");
  });

  it("displays correct error message when submit button is clicked with an empty field", () => {
    const inputCombos = [
      ["Customer ID", "Username"],
      ["Customer ID", "Password"],
      ["Username", "Password"],
    ];

    inputCombos.forEach((input) => {
      getInputByLabel(input[0]).type("input 1");
      getInputByLabel(input[1]).type("input 2");

      cy.get("button").click();
      cy.get("#loginError").should("have.text", "*All fields are required");

      //reset
      getInputByLabel(input[0]).clear();
      getInputByLabel(input[1]).clear();
    });
  });
  it("displays correct error message when submit button is clicked resulting in catch all error found", () => {
    getInputByLabel("Customer ID").type("input 1");
    getInputByLabel("Username").type("input 2");
    getInputByLabel("Password").type("input 3");

    cy.stub(window, "Worker");

    cy.get("button").click();
    cy.get("#loginError").should(
      "have.text",
      "*Internal error. Please try again later."
    );
  });
});
