/**
 * Add an extra leading zero when needed to the number (for use in the well name)
 *
 * @param {int} columnIndex - The column index within the labware
 * @param {bool} padding - Whether to zero-pad the number in the well name
 * @return {string}
 */
function _getFormattedColumnString(columnIndex, padding) {
  const columnNumber = columnIndex + 1;
  if (padding) {
    return "0" + columnNumber;
  } else {
    return columnNumber.toString();
  }
}

/** Allows calculations to convert between row, column, well index, and well name for Labware Definitions */
export class WellTitle {
  /**
   * Take pixel coordinates from a drawing and convert it back to the x/y numerical values that should have been used to generate those pixel coordinates.
   *
   * @param {int} numRows - The number of rows in the labware/plate
   * @param {int} numCols - The number of columns in the labware/plate
   */
  constructor(numRows, numCols) {
    this.numRows = numRows;
    this.numCols = numCols;
  }

  /**
   * Take pixel coordinates from a drawing and convert it back to the x/y numerical values that should have been used to generate those pixel coordinates.
   *
   * @throws {Error} If row or column index outside acceptable range (0-36 and 0-18) up to a 1536 well plate.
   */
  validateRowColumnCounts() {
    if (this.numRows < 1 || this.numRows > 18) {
      throw new Error(`Invalid number of rows: ${this.numRows}`);
    }
    if (this.numCols < 1 || this.numCols > 36) {
      throw new Error(`Invalid number of columns: ${this.numCols}`);
    }
  }

  /**
   * Get the well name from the row and column indices
   *
   * @param {int} rowIndex - The row index within the labware
   * @param {int} columnIndex - The column index within the labware
   * @param {bool} padding - Whether to zero-pad the number in the well name
   * @return {string}
   */
  getWellNameFromRowColumn(rowIndex, columnIndex, padding) {
    const rowChar = String.fromCharCode(65 + rowIndex);
    const columnChar = _getFormattedColumnString(columnIndex, padding);
    return rowChar + columnChar;
  }

  /**
   * Get the row and column indices from the well index
   *
   * @param {int} wellIndex - The well index within the labware
   * @return {Object} containing both the row index and well index (integers)
   */
  getRowColumnFromWellIndex(wellIndex) {
    const combo = {
      rowNum: 0,
      columnNum: 0,
    };
    this.validateRowColumnCounts();
    combo.rowNum = wellIndex % this.numRows;
    combo.columnNum = Math.floor(wellIndex / this.numRows);
    return combo;
  }

  /**
   * Get the alphanumeric well name from the well index
   *
   * @param {int} wellIndex - The well index within the labware
   * @param {bool} padding - Whether to zero-pad the number in the well name
   * @return {string} containing both the row index and well index (integers)
   */
  getWellNameFromIndex(wellIndex, padding) {
    let rowIndex = 0;
    let columnIndex = 0;
    const cellCombo = this.getRowColumnFromWellIndex(wellIndex);

    rowIndex = cellCombo.rowNum;
    columnIndex = cellCombo.columnNum;

    return this.getWellNameFromRowColumn(rowIndex, columnIndex, padding);
  }

  /**
   * Get the well index from the row and column indices
   *
   * @param {int} rowIndex - The row index within the labware
   * @param {int} columnIndex - The column index within the labware
   * @return {int}
   */
  getWellIndexFromRowColumn(rowIndex, columnIndex) {
    return columnIndex * this.numRows + rowIndex;
  }
  /**
   * Get the well index from well name
   *
   * @param {string} wellName
   * @returns {int}
   */
  getIndexFromWellName(wellName) {
    const row = wellName.charCodeAt(0) - "A".charCodeAt(0);
    const col = parseInt(wellName.slice(1)) - 1;
    const index = row * this.numCols + col;
    return index;
  }
}
