module matrix_transpose #(parameter ROWS = 10, parameter COLS = 10)(
    input clk,
    input rst,
    input start,
    input [7:0] a[0:ROWS-1][0:COLS-1],
    output reg [7:0] transpose[0:COLS-1][0:ROWS-1],
    output reg done
);

    integer i, j;
    reg [3:0] state;
    
    always @(posedge clk or posedge rst) begin
        if (rst) begin
            done <= 0;
            state <= 0;
        end else if (start) begin
            case (state)
                0: begin // Start Transposing
                    for (i = 0; i < ROWS; i = i + 1) begin
                        for (j = 0; j < COLS; j = j + 1) begin
                            transpose[j][i] <= a[i][j];
                        end
                    end
                    state <= 1;
                end
                1: begin // Done
                    done <= 1;
                end
            endcase
        end
    end

endmodule
