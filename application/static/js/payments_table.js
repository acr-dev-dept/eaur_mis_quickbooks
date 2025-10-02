$(document).ready(function() {
    let table = $('#payments-table').DataTable({
        processing: true,
        serverSide: true,
        ajax: {
            url: '/payments/get_payments',
            type: 'GET',
            data: function(d) {
                // Send the status filter value to Flask
                d.search = $('#status-filter').val(); // send as `search` so backend mapping works
            }
        },
        columns: [
            { data: 'id' },
            { data: 'reg_no' },
            { data: 'reference_number', defaultContent: '-' },
            { data: 'amount', defaultContent: 0 },
            { data: 'transaction_id', defaultContent: '-' },
            { data: 'payment_date', defaultContent: '-' },
            {
                data: 'status',
                render: function(data) {
                    if (data.toLowerCase() === 'synced') {
                        return '<span class="text-green-600 bg-green-100 px-2 py-1 rounded-md text-sm font-medium">Synced</span>';
                    } else if (data.toLowerCase() === 'unsynced') {
                        return '<span class="text-yellow-600 bg-yellow-100 px-2 py-1 rounded-md text-sm font-medium">Unsynced</span>';
                    } else if (data.toLowerCase() === 'failed') {
                        return '<span class="text-red-600 bg-red-100 px-2 py-1 rounded-md text-sm font-medium">Failed</span>';
                    } else {
                        return '<span class="badge badge-secondary">' + data + '</span>';
                    }
                }
            },
            { data: 'pushed_by', defaultContent: '-' },
            { data: 'pushed_date', defaultContent: '-' }
        ],
        order: [[0, 'desc']]
    });

    // hidden input to store selected status
    $("body").append('<input type="hidden" id="status-filter-input">');

    // buttons click → update hidden input + reload table
    $(".status-filter").on("click", function() {
        var status = $(this).data("status"); // gets "" / "synced" / "unsynced" / "failed"
        $("#status-filter-input").val(status);
        table.ajax.reload();
    });

        // Add hidden input to store selected status
    $("body").append('<input type="hidden" id="status-filter-input">');

    // Status button click → set active & reload table
    $(".status-filter").on("click", function() {
        // Remove active from all buttons
        $(".status-filter").removeClass("ring-2 ring-blue-500");

        // Add active state to clicked button
        $(this).addClass("ring-2 ring-blue-500");

        // Update hidden input and reload table
        var status = $(this).data("status");
        $("#status-filter-input").val(status);
        table.ajax.reload();
    });
});
